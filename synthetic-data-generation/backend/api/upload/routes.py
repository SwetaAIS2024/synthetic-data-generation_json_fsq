from fastapi import APIRouter, UploadFile, HTTPException, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from uuid import uuid4
import asyncio
from concurrent.futures import ThreadPoolExecutor
from models.YAMLConfig import YAMLConfig, SamplingParameters, PromptStructure, AdvancedOptions, DatasetParameters
from datetime import datetime
import yaml
import os

from config.celery import app

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/dataset/{config_id}")
async def upload_dataset(config_id: str):
    """
    Endpoint to trigger the upload of a generated dataset for a specific YAML config.
    
    Args:
        config_id: The ID of the YAML config for which to upload the dataset
        
    Returns:
        JSON response with status message
    """
    print(f"Received dataset upload request for config ID: {config_id}")
    
    try:
        # Verify the config exists
        try:
            yaml_config = YAMLConfig.objects.get(id=config_id)
            print(f"Found YAML config: {yaml_config.name}")
        except YAMLConfig.DoesNotExist:
            print(f"YAML config not found with ID: {config_id}")
            raise HTTPException(status_code=404, detail=f"YAML config with ID {config_id} not found")
        
        # Check if the config has any generated samples
        from models.SampleResponse import SampleResponse
        sample_count = SampleResponse.objects.filter(yaml_config_id=config_id).count()
        print(f"Found {sample_count} samples for config")
        
        if sample_count == 0:
            print(f"No samples found for config ID: {config_id}")
            raise HTTPException(status_code=400, detail="No samples found for this configuration")
            
        # Check if the dataset_id field is set
        if not yaml_config.dataset_id:
            # Generate a random dataset ID if not provided
            import uuid
            dataset_id = str(uuid.uuid4())
            print(f"Generated new dataset ID: {dataset_id}")
            yaml_config.dataset_id = dataset_id
            yaml_config.save()
        else:
            print(f"Using existing dataset ID: {yaml_config.dataset_id}")
        
        # Call the upload_dataset task
        try:
            task = app.send_task("modules.processor.upload_dataset", args=[config_id])
            print(f"Upload task created with ID: {task.id}")
        except Exception as task_error:
            print(f"Error creating task: {task_error}")
            raise HTTPException(status_code=500, detail=f"Failed to create upload task: {str(task_error)}")
        
        return JSONResponse({
            "message": "Dataset upload started",
            "config_id": config_id,
            "task_id": task.id,
            "dataset_id": yaml_config.dataset_id
        })
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        print(f"Unexpected error uploading dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/upload")
async def upload_yaml_config(file: UploadFile = File(...), name: str = Form(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        # Read file content
        contents = await file.read()

        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # Decode bytes to string and parse YAML content
        try:
            yaml_str = contents.decode('utf-8')
            yaml_data = yaml.safe_load(yaml_str)
            
            if not yaml_data:
                raise HTTPException(status_code=400, detail="Empty YAML file")
            
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML format: {str(e)}")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Invalid file encoding. Please use UTF-8")

        # Validate required fields
        if 'user_prompt' not in yaml_data:
            raise HTTPException(status_code=400, detail="Missing required field: user_prompt")
        
        if 'name' not in yaml_data:
            yaml_data['name'] = name

        if 'number_of_samples' not in yaml_data:
            raise HTTPException(status_code=400, detail="Missing required field: number_of_samples")

        # Ensure required_criteria is correctly processed as a list of strings
        req_criteria = yaml_data.get('required_criteria', [])
        if isinstance(req_criteria, list):
            # Make sure each item is a string
            req_criteria = [str(item) for item in req_criteria]
        else:
            # If it's not a list, make it a list with one item
            req_criteria = [str(req_criteria)]

        # Ensure example_inputs is also a list of strings
        example_inputs = yaml_data.get('example_inputs', [])
        if isinstance(example_inputs, list):
            example_inputs = [str(item) for item in example_inputs]
        else:
            example_inputs = [str(example_inputs)] if example_inputs else []

        # Extract or create nested structures
        sampling_params = SamplingParameters(
            temperature_range=yaml_data.get('sampling_parameters', {}).get('temperature_range') or yaml_data.get('parameters', {}).get('temperature_range') or [0.7, 1.0], 
            top_p=yaml_data.get('sampling_parameters', {}).get('top_p') or yaml_data.get('parameters', {}).get('top_p') or 0.9
        )
        
        prompt_structure = PromptStructure(
            user_prompt_template=yaml_data.get('prompt_structure', {}).get('user_prompt_template', yaml_data.get('user_prompt', '')),
            language_style=yaml_data.get('prompt_structure', {}).get('language_style', 'professional')
        )
        
        advanced_options = AdvancedOptions(
            strict_mode=yaml_data.get('advanced_options', {}).get('strict_mode', yaml_data.get('strict_mode', True))
        )
        
        # Make sure validation_rules is a list of strings
        validation_rules = yaml_data.get('dataset_parameters', {}).get('validation_rules') or yaml_data.get('validation_rules', [])
        if isinstance(validation_rules, list):
            validation_rules = [str(item) for item in validation_rules]
        else:
            validation_rules = [str(validation_rules)] if validation_rules else []
            
        dataset_params = DatasetParameters(
            output_format=yaml_data.get('dataset_parameters', {}).get('output_format') or yaml_data.get('output_format', 'jsonl'),
            task_description=yaml_data.get('dataset_parameters', {}).get('task_description') or yaml_data.get('task_description', ''),
            max_tokens=yaml_data.get('dataset_parameters', {}).get('max_tokens') or yaml_data.get('parameters', {}).get('max_tokens', 1024),
            seed_value=yaml_data.get('dataset_parameters', {}).get('seed_value') or yaml_data.get('parameters', {}).get('seed_value', 42),
            validation_rules=validation_rules
        )

        # Process the user_prompt template (ensuring it's properly formatted)
        user_prompt = yaml_data['user_prompt']
        
        # Create YAMLConfig document with the new structure
        yaml_config = YAMLConfig(
            name=yaml_data.get('name', name),
            number_of_samples=yaml_data['number_of_samples'],
            user_prompt=user_prompt,  # Store the original prompt
            model=yaml_data.get('model', 'gpt-4o-mini'),
            required_criteria=req_criteria,  # Use our processed list of criteria
            example_inputs=example_inputs,  # Use our processed list of examples
            # Embedded documents
            sampling_parameters=sampling_params,
            prompt_structure=prompt_structure,
            advanced_options=advanced_options,
            dataset_parameters=dataset_params,
            # Store the original YAML
            raw_yaml=yaml_str
        ).save()

        app.send_task("modules.processor.process_yaml_config", args=[str(yaml_config.id)])

        return JSONResponse({
            "message": "YAML config uploaded successfully",
            "config_id": str(yaml_config.id),
            "name": yaml_data.get('name', name),
        })

    except Exception as e:
        print(f"Error processing YAML upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def root():
    return {"message": "Email Upload API"}


@router.get("/dataset/{config_id}")
async def get_dataset_test(config_id: str):
    """
    GET endpoint for testing the dataset upload route directly from browser
    Can be accessed at: http://localhost:5000/api/upload/dataset/{config_id}
    """
    print(f"BROWSER TEST: Received GET request for config ID: {config_id}")
    
    # Return a simple test response
    return JSONResponse({
        "message": "GET test successful - this means the route is accessible",
        "config_id": config_id,
        "test": True,
        "browser_test": True,
        "next_step": "Try the POST request from your frontend now"
    })

@router.get("/download/{config_id}")
async def download_dataset(config_id: str):
    """
    Endpoint to download a generated dataset for a specific YAML config.
    
    Args:
        config_id: The ID of the YAML config for which to download the dataset
        
    Returns:
        FileResponse containing the JSONL dataset file
    """
    print(f"Received dataset download request for config ID: {config_id}")
    
    try:
        # Verify the config exists
        try:
            yaml_config = YAMLConfig.objects.get(id=config_id)
            print(f"Found YAML config: {yaml_config.name}")
        except YAMLConfig.DoesNotExist:
            print(f"YAML config not found with ID: {config_id}")
            raise HTTPException(status_code=404, detail=f"YAML config with ID {config_id} not found")
        
        # Check if generation is complete (don't require formal upload)
        from models.SampleResponse import SampleResponse
        sample_count = SampleResponse.objects.filter(yaml_config_id=config_id).count()
        print(f"Found {sample_count} samples for config")
        
        if sample_count == 0:
            print(f"No samples found for config ID: {config_id}")
            raise HTTPException(status_code=400, detail="No samples have been generated for this configuration")
            
        # If dataset file doesn't exist yet but generation is complete, create it on-demand
        datasets_dir = "datasets"
        os.makedirs(datasets_dir, exist_ok=True)
        dataset_filename = f"{config_id}.jsonl"
        dataset_path = os.path.join(datasets_dir, dataset_filename)
        
        # Check if file exists, if not create it
        if not os.path.exists(dataset_path):
            print(f"Dataset file not found at {dataset_path}. Creating it now...")
            
            import json
            # Get all samples and create JSONL file
            samples = SampleResponse.objects.filter(yaml_config_id=config_id)
            
            with open(dataset_path, 'w') as f:
                for idx, sample in enumerate(samples):
                    try:
                        # Try to parse the response_text as JSON if it's a string
                        if isinstance(sample.response_text, str):
                            try:
                                # Parse if it's a JSON string
                                if sample.response_text.strip().startswith('{') and sample.response_text.strip().endswith('}'):
                                    parsed = json.loads(sample.response_text)
                                    if 'messages' in parsed and len(parsed['messages']) == 2:
                                        # Use the parsed messages directly
                                        f.write(json.dumps(parsed) + '\n')
                                        continue
                            except json.JSONDecodeError:
                                print(f"Sample {idx} couldn't be parsed as JSON, using fallback")
                        
                        # Fallback: Create a proper fine-tuning entry
                        if getattr(sample, 'input_request', None) and sample.response_text:
                            entry = {
                                "messages": [
                                    {"role": "user", "content": sample.input_request},
                                    {"role": "assistant", "content": sample.response_text}
                                ]
                            }
                            f.write(json.dumps(entry) + '\n')
                        else:
                            # Just write the response text
                            sanitized_text = sample.response_text.replace('\n', ' ').replace('\r', ' ')
                            f.write(f"{sanitized_text}\n")
                    
                    except Exception as e:
                        print(f"Error processing sample {idx}: {e}")
            
            print(f"Successfully created dataset file at {dataset_path}")
            
        # Return the file as an attachment with a specific filename
        return FileResponse(
            path=dataset_path, 
            filename=f"{yaml_config.name.replace(' ', '_')}_dataset.jsonl",
            media_type="application/jsonl"
        )
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        print(f"Unexpected error downloading dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

