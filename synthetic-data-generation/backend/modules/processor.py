from __future__ import absolute_import
from config.celery import app
import time
from config.db import connect_db
from datetime import datetime
from models.YAMLConfig import YAMLConfig
from modules.llm_client import LLMClient
import os
from config.config import Config
from mongoengine import Document
import yaml
from models.GenerationRequest import GenerationRequest
from models.ResponseStructure import ResponseStructure
from models.SampleResponse import SampleResponse
import json
from celery import chord

# Initialize database connection
connect_db()

# YAML structure guide for generation
YAML_STRUCTURE_GUIDE = """
# Configuration generated for {dataset_name} dataset
# Generated at: {current_datetime}

name: <string> # A descriptive name for the configuration.
model: <string> # Model identifier, e.g., 'accounts/fireworks/models/deepseek-v3'
number_of_samples: <integer> # Number of samples to generate, e.g., 150
output_format: <string> # Format of output data, e.g., 'jsonl', 'csv', 'bullet points'

# Sampling parameters for controlling response generation
parameters:
  temperature_range: [<float>, <float>]  # Controls response randomness, e.g. [0.1, 0.3]
  top_p: <float>  # Nucleus sampling parameter, e.g. 0.9
  max_tokens: <integer> # Maximum number of tokens per response, e.g., 750
  seed_value: <integer> # Random seed for reproducibility, e.g., 42

# Required fields for system functionality
# Essential field - must be included for uploading to work
user_prompt: |
  <string> # Main instruction prompt for the LLM
  You are creating a synthetic dataset for AI training. The dataset should follow this format:
  
  ```json
  {
    "messages": [
      {"role": "user", "content": "A specific user request or question"},
      {"role": "assistant", "content": "A high-quality, detailed response"}
    ]
  }
  ```
  
  Context for this dataset: {input_request}
  
  Generate a realistic user request AND an ideal assistant response that perfectly demonstrates the type of interaction described above.
  Make sure both the user query and assistant response are detailed, high-quality, and representative of real-world scenarios.
  
  IMPORTANT: Return ONLY the JSON object with the messages array containing exactly one user message and one assistant message.
  Do not include any explanations or additional text. The output must be valid JSON.

# Detailed structure for generating prompts (can include the same content as user_prompt)
prompt_structure:
  user_prompt_template: |
    [Task] <brief task description based on the user request>
    [Requirements]
    - <key requirement 1>
    - <key requirement 2>
    - <...more requirements as needed>
    [Input Data]
    <input field name>: {<placeholder>}
    [Format]
    Output: <expected output format>
  language_style: <style descriptors, e.g., "formal", "technical", "concise">

# Task description
task_description: <string> # A concise description of the generation task

# Required criteria for response validation
required_criteria:
  - <criterion 1>
  - <criterion 2>
  - <criterion 3>

# YAML configuration behavior
strict_mode: <boolean> # Whether to enforce strict validation of responses

# Dataset-specific parameters
dataset_parameters:
  output_format: <format>  # e.g., "jsonl", "bullet points", "python_code"
  task_description: <detailed task description>
  max_tokens: <integer>
  seed_value: <integer>
  validation_rules:
    - <rule 1>
    - <rule 2>
    - <...more rules as needed>

# Quality control parameters
quality_controls:
  response_validation:
    min_length: <integer>
    max_length: <integer>
    required_elements:
      - <required element 1>
      - <required element 2>
      - <...more elements as needed>
    forbidden_elements:
      - <forbidden element 1>
      - <forbidden element 2>
      - <...more elements as needed>
  diversity_controls:
    min_unique_words: <integer>
    max_repetition: <float>
    style_variation: <float>
  consistency_checks:
    context_window: <integer>
    style_consistency: <float>
    fact_consistency: <float>

# Diversity parameters
diversity_parameters:
  variation_controls:
    temperature_variation: <float>
    style_variation: <float>
    complexity_variation: <float>
  sampling_strategy:
    method: <method name>  # e.g., "stratified", "uniform"
    min_unique_ratio: <float>
    max_similarity: <float>
  content_balancing:
    topic_distribution: <distribution type>  # e.g., "equal", "uniform"
    difficulty_levels:
      - <level 1>
      - <level 2>
      - <level 3>
    style_distribution:
      - <style 1>
      - <style 2>
      - <style 3>

# Evaluation metrics
evaluation_metrics:
  quality_metrics:
    coherence_score: <float>
    relevance_score: <float>
    completeness_score: <float>
  diversity_metrics:
    vocabulary_richness: <float>
    syntactic_diversity: <float>
    semantic_diversity: <float>
  consistency_metrics:
    factual_accuracy: <float>
    style_consistency: <float>
    context_relevance: <float>

# Example inputs. Be as diverse as possible, these examples will be used to generate the dataset. Wrap them in "double quotes" (at least 75)
example_inputs:
  - <example input 1>
  - <example input 2>
  - <example input 3>
  - <example input 4>
  - <example input 5>
  - <example input 6>
  - <example input 7>
  - <example input 8>
  - <example input 9>
  - <example input 10>
  - <...more example inputs until you have at least 75>
"""

@app.task
def process_yaml_config(mongo_id):
    """Task to process a YAML config"""
    print(f"Starting YAML config processing for ID: {mongo_id}")

    try:
        yaml_config = YAMLConfig.objects.get(id=mongo_id)
        
        # Get the example inputs from the YAML config
        example_inputs = yaml_config.example_inputs
        if not example_inputs:
            print("Warning: No example inputs found in YAML config, will use placeholder input")
            example_inputs = ["Create a sample dataset entry relevant to this topic"]
            
        print(f"Found {len(example_inputs)} example inputs in YAML config")

        # Create a group of tasks for sample generation
        sample_tasks = []
        
        # Base prompt template
        prompt_template = yaml_config.user_prompt
        
        # Check if the prompt template contains the input placeholder
        if "{input_request}" not in prompt_template:
            print("Warning: No {input_request} placeholder found in prompt template")
            print(f"Original prompt: {prompt_template}")
            # Add a placeholder at the end if not present
            prompt_template += "\n\nContext for this dataset: {input_request}"
            print(f"Modified prompt: {prompt_template}")
            
        # Make sure the prompt has clear instructions
        if "IMPORTANT: Return ONLY the JSON object" not in prompt_template:
            print("Adding JSON formatting instructions to prompt")
            json_instructions = """
            
IMPORTANT: Return ONLY the JSON object with the messages array containing exactly one user message and one assistant message.
Do not include any explanations or additional text. The output must be valid JSON.
"""
            prompt_template += json_instructions
            
        import random
        
        for i in range(yaml_config.number_of_samples):
            # Generate a random temperature within the specified range
            min_temp, max_temp = yaml_config.temperature_range
            temperature = min_temp + (max_temp - min_temp) * (i / max(1, yaml_config.number_of_samples - 1))
            
            # Select a random example input
            selected_input = random.choice(example_inputs)
            
            # Clean up the input - remove quotes if present
            if selected_input.startswith('"') and selected_input.endswith('"'):
                selected_input = selected_input[1:-1]
                
            # Create the complete prompt by substituting the selected input
            complete_prompt = prompt_template.replace("{input_request}", selected_input)
            
            print(f"Sample {i+1}/{yaml_config.number_of_samples} - Using example input: {selected_input[:50]}...")
            
            # Send task to generate sample response and collect task result
            task = generate_sample_response.delay(
                str(yaml_config.id),
                temperature,
                yaml_config.top_p,
                complete_prompt,
                yaml_config.max_tokens,
                yaml_config.seed_value,
                yaml_config.model,
                yaml_config.output_format
            )
            sample_tasks.append(task)
    
    except Exception as e:
        import traceback
        print(f"Error processing YAML config: {e}")
        print(traceback.format_exc())
        return False
    
    return True

@app.task
def upload_dataset(yaml_config_id):
    """
    Task to upload a dataset to Fireworks AI after all samples have been generated.
    
    Args:
        yaml_config_id: ID of the YAML config with the generated samples
    """
    print(f"Starting dataset upload task for YAML config ID: {yaml_config_id}")
    
    try:
        import os
        import json
        # Log current working directory to help debug path issues
        current_dir = os.getcwd()
        print(f"Current working directory: {current_dir}")
        
        from .llm_client import LLMClient
        from config.config import Config
        from models.SampleResponse import SampleResponse
        
        # Get the YAML config
        yaml_config = YAMLConfig.objects.get(id=yaml_config_id)
        print(f"Processing YAML config: {yaml_config.name}")
        
        # Use a simple path within Docker container
        datasets_dir = "datasets"
        os.makedirs(datasets_dir, exist_ok=True)
        print(f"Using datasets directory: {os.path.abspath(datasets_dir)}")
        
        # Create the dataset filename (just the ID + .jsonl)
        dataset_filename = f"{yaml_config_id}.jsonl"
        dataset_path = os.path.join(datasets_dir, dataset_filename)
        print(f"Will write dataset to: {os.path.abspath(dataset_path)}")
        
        # Combine all generated samples into a single dataset file
        # Each line will be a properly formatted JSONL entry for fine-tuning
        samples = SampleResponse.objects.filter(yaml_config_id=yaml_config_id)
        sample_count = samples.count()
        print(f"Found {sample_count} samples to include in dataset")
        
        with open(dataset_path, 'w') as f:
            for idx, sample in enumerate(samples):
                try:
                    # Try to parse the response_text as JSON if it's a string
                    # This handles both when response_text is already JSON and when it's a string
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
                    # If we have both content fields, create a messages array
                    if getattr(sample, 'input_request', None) and sample.response_text:
                        entry = {
                            "messages": [
                                {"role": "user", "content": sample.input_request},
                                {"role": "assistant", "content": sample.response_text}
                            ]
                        }
                        f.write(json.dumps(entry) + '\n')
                    else:
                        # Just write the response text (might not be ideal for finetuning)
                        sanitized_text = sample.response_text.replace('\n', ' ').replace('\r', ' ')
                        f.write(f"{sanitized_text}\n")
                
                except Exception as e:
                    print(f"Error processing sample {idx}: {e}")
                
                if idx % 50 == 0 and idx > 0:
                    print(f"  Processed {idx}/{sample_count} samples...")
        
        print(f"Successfully wrote dataset file to {dataset_path}")
        file_size = os.path.getsize(dataset_path)
        print(f"Dataset file size: {file_size/1024:.2f} KB")
        
        # Print a message about where the file can be found
        print(f"\n=== IMPORTANT: Your dataset file has been created at {os.path.abspath(dataset_path)} ===\n")
        
        # For testing only - early return before actual API call
        if not Config.FIREWORKS_API_KEY or not Config.FIREWORKS_ACCOUNT_ID:
            print("WARNING: FIREWORKS_API_KEY or FIREWORKS_ACCOUNT_ID not set, skipping actual API upload")
            yaml_config.dataset_uploaded = False
            yaml_config.dataset_upload_response = {"error": "API credentials not configured"}
            yaml_config.save()
            return {"status": "file_created_only", "error": "API credentials not configured", "file_path": os.path.abspath(dataset_path)}
            
        # Generate dataset ID if not already set
        if not yaml_config.dataset_id:
            import uuid
            yaml_config.dataset_id = str(uuid.uuid4())
            yaml_config.save()
            
        # Create a full dataset ID with prefix to ensure uniqueness
        full_dataset_id = f"generatedsyntheticdataset{yaml_config.dataset_id}"
        print(f"Using dataset ID: {full_dataset_id}")
            
        print(f"Initializing LLMClient for dataset operations")
        # Initialize the client
        client = LLMClient(api_key=Config.FIREWORKS_API_KEY)
        
        # First, create the dataset
        print(f"Creating dataset in Fireworks AI - Account: {Config.FIREWORKS_ACCOUNT_ID}, Dataset ID: {full_dataset_id}")
        create_response = client.create_dataset(
            account_id=Config.FIREWORKS_ACCOUNT_ID,
            dataset_id=full_dataset_id,
            display_name=f"Generated Dataset - {yaml_config.name}"
        )
        
        print(f"Dataset creation response: {create_response}")
        
        # Check if dataset creation was successful
        if "error" in create_response:
            print(f"Error creating dataset: {create_response['error']}")
            yaml_config.dataset_upload_response = create_response
            yaml_config.save()
            return create_response
            
        # Now upload the data to the created dataset
        print(f"Using local dataset path for upload: {os.path.abspath(dataset_path)}")
        print(f"Uploading dataset to Fireworks AI - Account: {Config.FIREWORKS_ACCOUNT_ID}, Dataset ID: {full_dataset_id}")
        
        # Use the local path directly - Docker container will have access to this
        upload_response = client.upload_dataset(
            file_path=os.path.abspath(dataset_path),
            account_id=Config.FIREWORKS_ACCOUNT_ID,
            dataset_id=full_dataset_id
        )
        
        print(f"Upload response: {upload_response}")
        
        # Combine responses
        response = {
            "creation": create_response,
            "upload": upload_response,
            "file_path": os.path.abspath(dataset_path),
            "dataset_id": full_dataset_id
        }
        
        # Update the YAML config with upload status
        yaml_config.dataset_uploaded = True
        yaml_config.dataset_upload_response = response
        yaml_config.save()
        
        print(f"Dataset created and uploaded successfully for YAML config {yaml_config_id}")
        return response
        
    except Exception as e:
        print(f"Error uploading dataset: {e}")
        import traceback
        print(traceback.format_exc())
        return {"error": str(e)}

async def generate_yaml_config(request: GenerationRequest):
    """
    Generates a YAML configuration file based on the user's description.
    
    Args:
        request: GenerationRequest object containing a description for the data generation task
        
    Returns:
        Dictionary containing the generated YAML configuration
    """
    print(f"Received generation request: {request.description}")

    # Instantiate the LLM Client (using defaults from config)
    llm_client = LLMClient()

    # Extract a dataset name from the request
    # Remove spaces, lowercase, and use underscores
    dataset_name = '_'.join(request.description.lower().split()[:3])
    
    # Get current datetime
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")

    # Construct the prompt for the LLM
    prompt = f"""
You are a specialist in creating detailed YAML configuration files for synthetic data generation.

User Request: "{request.description}"

Based on this request, create a comprehensive YAML configuration file following these guidelines:

1. The YAML should define parameters for generating synthetic data as described in the user request.
2. Be specific and detailed when defining parameters, prompt templates, and criteria.
3. Choose appropriate validation rules and quality controls that match the data type requested.
4. Create a prompt template that would effectively instruct an LLM to generate the requested data.
5. Include reasonable example inputs that would work with this configuration.
6. IMPORTANT: Make sure to include ALL the required fields, especially 'name', 'model', 'number_of_samples', 'output_format', 'parameters', 'user_prompt', 'task_description', 'required_criteria', and 'strict_mode'.
7. Use the format below, replacing placeholders with appropriate values.

CRITICAL YAML FORMATTING RULES:
- NEVER use commas to separate key-value pairs on a single line
- Each key-value pair must be on its own line with proper indentation
- Example inputs must be properly indented as a YAML list
- Maps/objects must use proper indentation, not inline format
- For more complex values, use the multi-line string format with pipe (|) character
- Never use tabs, only spaces for indentation
- Be extremely careful with indentation consistency

Current date/time: {current_datetime}
Dataset name suggestion: {dataset_name}

{YAML_STRUCTURE_GUIDE}

IMPORTANT:
1. Make sure all placeholder values are replaced with appropriate content relevant to the user's specific request.
2. Values in angle brackets <> must be replaced with actual values.
3. The 'user_prompt' field MUST be included as a top-level field for the upload to work.
4. Ensure both 'user_prompt' and 'prompt_structure.user_prompt_template' contain appropriate prompts.
5. All YAML content must be properly indented and follow YAML syntax rules.
6. NEVER use commas to separate multiple key-value pairs on a single line.
7. DO NOT include ```yaml at the beginning of the YAML file or ``` at the end.
8. Ensure colons (:) are only used for key-value pairs and properly followed by a space - avoid colons within text fields as they can break YAML parsing
"""

    try:
        print("Sending request to LLM...")
        generated_yaml = llm_client.generate_text(prompt=prompt)
        print("Received response from LLM.")

        # Basic validation: Check if the output looks like YAML
        try:
            # Attempt to load the YAML to catch basic syntax errors
            parsed_yaml = yaml.safe_load(generated_yaml)
            print("Generated YAML is valid.")
            
            # Check for required fields
            missing_fields = []
            required_fields = ['name', 'model', 'number_of_samples', 'output_format', 'parameters', 'user_prompt']
            
            for field in required_fields:
                if field not in parsed_yaml:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"Warning: Missing required fields: {', '.join(missing_fields)}")
                # You might want to regenerate or fix the YAML here
        
        except yaml.YAMLError as e:
            print(f"Generated content is not valid YAML: {e}")
            # Try to clean up common YAML formatting issues
            lines = generated_yaml.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Replace commas between key-value pairs
                if ': ' in line and ', ' in line.split(': ', 1)[1]:
                    # This line might have comma-separated key-value pairs
                    base_indent = len(line) - len(line.lstrip())
                    key_part = line.split(':', 1)[0]
                    value_part = line.split(':', 1)[1].strip()
                    
                    # If it looks like multiple key-value pairs
                    if ', ' in value_part and ': ' in value_part:
                        # Replace the line with properly formatted YAML
                        cleaned_lines.append(line.split(',', 1)[0])  # Keep first key-value pair
                        
                        # Add remaining pairs with proper indentation
                        pairs = value_part.split(', ')
                        for pair in pairs[1:]:
                            if ': ' in pair:
                                cleaned_lines.append(' ' * base_indent + pair)
                    else:
                        cleaned_lines.append(line)
                else:
                    cleaned_lines.append(line)
            
            # Try parsing again with cleaned content
            cleaned_yaml = '\n'.join(cleaned_lines)
            try:
                yaml.safe_load(cleaned_yaml)
                print("Cleaned YAML is now valid.")
                generated_yaml = cleaned_yaml
            except yaml.YAMLError as e2:
                print(f"Still invalid after cleaning: {e2}")
                # Just return the original with a warning

        # Return the generated YAML string
        return {"yaml": generated_yaml.strip()}

    except Exception as e:
        print(f"Error during LLM call or processing: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to generate YAML using LLM: {str(e)}")


@app.task
def generate_sample_response(yaml_config_id, temperature, top_p, prompt, max_tokens, seed_value, model, output_format):
    """Task to generate a sample response based on YAML config parameters"""
    print(f"Generating sample response for YAML config ID: {yaml_config_id}")
    
    try:
        # Import the SampleResponse model
        from models.SampleResponse import SampleResponse
        import json
        
        # Initialize LLM client
        llm_client = LLMClient()
        
        # Start measuring time
        start_time = time.time()
        
        # Try to extract the input request from the prompt, if available
        input_request = None
        if "Context for this dataset:" in prompt:
            parts = prompt.split("Context for this dataset:")
            if len(parts) > 1:
                input_request = parts[1].strip()
                # Remove any trailing instructions
                if "Generate a realistic" in input_request:
                    input_request = input_request.split("Generate a realistic")[0].strip()
                print(f"Extracted input request: {input_request[:50]}...")
        
        # Generate response with streaming to measure metrics
        print(f"Sending prompt to model {model} with temperature {temperature}")
        response_text, metrics = llm_client.generate_structured_response_with_metrics(
            prompt=prompt,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            model=model,
            schema_model=ResponseStructure
        )
        
        print(f"Received response: {response_text[:100]}...")
        
        # Clean up and validate the response
        # If we get pure JSON, make sure it's properly parsed
        try:
            # See if we need to parse JSON from the response
            if isinstance(response_text, str) and (response_text.strip().startswith('{') and response_text.strip().endswith('}')):
                parsed_response = json.loads(response_text)
                # Ensure it has the expected structure
                if 'messages' in parsed_response and isinstance(parsed_response['messages'], list):
                    if len(parsed_response['messages']) == 2:
                        print("Successfully parsed JSON response with correct structure")
                    else:
                        print(f"Warning: JSON has {len(parsed_response['messages'])} messages instead of 2")
                else:
                    print("Warning: JSON response missing 'messages' array")
            else:
                # It's already processed by the schema model
                print("Response already processed by schema model")
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse response as JSON: {e}")
        
        # Calculate total latency
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Store the sample response with metrics
        sample_response = SampleResponse(
            yaml_config_id=yaml_config_id,
            temperature=temperature,
            top_p=top_p,
            prompt=prompt,
            input_request=input_request,  # Store the extracted input request
            max_tokens=max_tokens,
            seed_value=seed_value,
            model=model,
            response_text=response_text,
            tokens_per_second=metrics.get('tokens_per_second', 0.0),
            time_to_first_token=metrics.get('time_to_first_token', 0.0) * 1000,  # Convert to milliseconds
            latency=latency_ms,
            total_tokens=metrics.get('total_tokens', 0)
        ).save()
        
        # Use atomic operations to update the YAML config metrics
        # This prevents race conditions when multiple workers update the same document
        
        # Calculate QPS
        qps = 1000 / latency_ms if latency_ms > 0 else 0
        
        # Use atomic increment and MongoDB's $inc operator (through MongoEngine)
        YAMLConfig.objects(id=yaml_config_id).update_one(
            # Increment the total responses count
            inc__total_responses_generated=1,
            # Update the sum of metrics - we'll calculate averages in the frontend/getter
            inc__tokens_per_second_sum=metrics.get('tokens_per_second', 0.0),
            inc__time_to_first_token_sum=metrics.get('time_to_first_token', 0.0) * 1000,  # Convert to milliseconds
            inc__queries_per_second_sum=qps,
            inc__average_latency_sum=latency_ms,
            inc__total_tokens_sum=metrics.get('total_tokens', 0)
        )
        
        print(f"Sample response generated successfully for YAML config ID: {yaml_config_id}")
        return True
        
    except Exception as e:
        import traceback
        print(f"Error generating sample response: {e}")
        print(traceback.format_exc())
        return False