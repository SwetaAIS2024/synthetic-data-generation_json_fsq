import os
import json
import base64
import requests
from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, Field
import openai
from config.config import Config

class LLMClient:
    """
    Client for interacting with Fireworks AI LLM API using OpenAI SDK.
    Supports structured JSON responses and document inlining.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "accounts/fireworks/models/llama-v3p3-70b-instruct",
                 max_tokens: int = 4096,
                 temperature: float = 0.6):
        """
        Initialize the Fireworks LLM client.
        
        Args:
            api_key: API key for the Fireworks service (defaults to environment variable)
            model: Model identifier to use
            max_tokens: Maximum tokens to generate in the response
            temperature: Controls randomness in generation (0.0-1.0)
        """
        self.api_key = api_key or Config.FIREWORKS_API_KEY
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Initialize OpenAI client with Fireworks base URL
        self.client = openai.OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=self.api_key,
        )
        
    def _create_message_with_documents(self, prompt: str, documents: Dict[str, str] = None) -> List[Dict]:
        """
        Create a message that includes document references using document inlining.
        
        Args:
            prompt: The text prompt
            documents: Dictionary of document paths and their file paths or base64 content
            
        Returns:
            List of message dictionaries for the API call
        """
        if not documents:
            return [{"role": "user", "content": prompt}]
        
        # Use the format from Approach 2 that was successful in testing
        content_parts = [{"type": "text", "text": prompt}]
        
        # Add each document as an image_url with proper nesting and transform in the URL
        for doc_name, doc_path in documents.items():
            if os.path.exists(doc_path):
                try:
                    # For PDFs
                    if doc_path.lower().endswith('.pdf'):
                        with open(doc_path, 'rb') as file:
                            base64_content = base64.b64encode(file.read()).decode('utf-8')
                            # Use the successful approach: transform=inline in URL
                            url_with_transform = f"data:application/pdf;base64,{base64_content}#transform=inline"
                            
                            # Add with the exact format from successful Approach 2
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": url_with_transform
                                }
                            })
                            print(f"Added document: {doc_name} ({os.path.getsize(doc_path)/1024:.1f} KB)")
                except Exception as e:
                    print(f"Error processing document {doc_name}: {e}")
        
        return [{"role": "user", "content": content_parts}]
        
    def generate_text(self, prompt: str, documents: Dict[str, str] = None) -> str:
        """
        Generate free-form text from the LLM based on the prompt and optional documents.
        
        Args:
            prompt: The input prompt for the LLM
            documents: Dictionary of document names and their file paths or URLs
            
        Returns:
            Generated text response
        """
        try:
            messages = self._create_message_with_documents(prompt, documents)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating text response: {e}")
            return f"Error generating response: {str(e)}"
    
    def generate_structured_json(self, prompt: str, schema_model: BaseModel, 
                                documents: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Generate a structured JSON response from the LLM based on a Pydantic schema.
        
        Args:
            prompt: The input prompt for the LLM
            schema_model: Pydantic model defining the expected JSON structure
            documents: Dictionary of document names and their file paths or URLs
            
        Returns:
            Dictionary containing the parsed JSON response
        """
        # Set to True to bypass document processing temporarily
        DISABLE_DOCUMENTS = False
        
        if DISABLE_DOCUMENTS:
            documents = None
        
        try:
            messages = self._create_message_with_documents(prompt, documents)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object", "schema": schema_model.model_json_schema()},
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            json_content = response.choices[0].message.content
            
            # Debug print to see raw response
            print(f"Raw JSON response: {json.dumps(json.loads(json_content), indent=2)}")
            
            parsed_content = json.loads(json_content)
            
            # Ensure explanation field exists
            if 'explanation' in schema_model.model_fields and 'explanation' not in parsed_content:
                parsed_content['explanation'] = "No explanation provided by the model."
                
            return parsed_content
        except Exception as e:
            print(f"Error generating structured JSON response: {e}")
            # Return empty dict with expected keys from the schema
            default_values = {}
            
            # Build default values from schema including explanation fields
            for field_name, field in schema_model.model_fields.items():
                if field_name == 'explanation':
                    default_values[field_name] = f"Error generating explanation: {str(e)}"
                elif field.annotation == str:
                    default_values[field_name] = ""
                elif field.annotation in (int, float):
                    default_values[field_name] = 0
                elif field.annotation == bool:
                    default_values[field_name] = False
                elif field.annotation == list:
                    default_values[field_name] = []
                elif field.annotation == dict:
                    default_values[field_name] = {}
                else:
                    # Handle nested models by checking if they have default factories
                    if hasattr(field, 'default_factory') and field.default_factory is not None:
                        default_values[field_name] = field.default_factory()
                    else:
                        default_values[field_name] = None
            return default_values 

    def generate_response_with_metrics(self, prompt, temperature=0.7, top_p=1.0, max_tokens=1000, seed=None, model="accounts/fireworks/models/deepseek-v3"):
        """
        Generate a response from the LLM with performance metrics.
        
        Returns:
            tuple: (response_text, metrics_dict)
        """
        try:
            import time
            
            # Start measuring time
            start_time = time.time()
            first_token_time = None
            total_tokens = 0
            response_text = ""
            
            # Generate response with streaming to measure metrics
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                #seed=seed,
                stream=True  # Enable streaming
            )
            
            # Process the stream to capture metrics
            for chunk in response:
                if first_token_time is None:
                    # Capture time when the first token is received
                    first_token_time = time.time() - start_time
                
                # Extract the content from the chunk
                content = chunk.choices[0].delta.content
                if content:
                    response_text += content
                    # Approximate token count (rough estimate)
                    total_tokens += len(content) / 4  # ~4 characters per token on average
            
            # Calculate end time and total duration
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate tokens per second
            tokens_per_second = total_tokens / total_time if total_time > 0 else 0
            
            # If first_token_time is still None (no tokens received), set to total_time
            if first_token_time is None:
                first_token_time = total_time
            
            # Compile metrics
            metrics = {
                "time_to_first_token": first_token_time,  # In seconds
                "total_tokens": int(total_tokens),
                "tokens_per_second": tokens_per_second,
                "total_time": total_time  # In seconds
            }
            
            return response_text, metrics
            
        except Exception as e:
            print(f"Error generating response with metrics: {e}")
            return "", {
                "time_to_first_token": 0,
                "total_tokens": 0,
                "tokens_per_second": 0,
                "total_time": 0
            } 
        
    def generate_structured_response_with_metrics(self, prompt, schema_model, temperature=0.7, top_p=1.0, max_tokens=1000, seed=None, model="accounts/fireworks/models/deepseek-v3"):
        """
        Generate a structured JSON response from the LLM with performance metrics.
        
        Returns:
            tuple: (response_text, metrics_dict)
        """ 
        try:
            import time
            
            # Start measuring time
            start_time = time.time()
            first_token_time = None
            total_tokens = 0
            response_text = ""
            
            # Generate response with streaming to measure metrics
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object", "schema": schema_model.model_json_schema()},
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                #seed=seed,
                stream=True  # Enable streaming
            )   
            
            # Process the stream to capture metrics
            for chunk in response:
                if first_token_time is None:
                    # Capture time when the first token is received
                    first_token_time = time.time() - start_time
                
                # Extract the content from the chunk
                content = chunk.choices[0].delta.content
                if content:
                    response_text += content
                    # Approximate token count (rough estimate)
                    total_tokens += len(content) / 4  # ~4 characters per token on average
                    
            # Calculate end time and total duration
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate tokens per second
            tokens_per_second = total_tokens / total_time if total_time > 0 else 0
            
            # If first_token_time is still None (no tokens received), set to total_time
            if first_token_time is None:
                first_token_time = total_time
            
            # Compile metrics
            metrics = {
                "time_to_first_token": first_token_time,  # In seconds
                "total_tokens": int(total_tokens),
                "tokens_per_second": tokens_per_second,
                "total_time": total_time  # In seconds
            }
            
            return response_text, metrics

        except Exception as e:
            print(f"Error generating structured response with metrics: {e}")
            return "", {
                "time_to_first_token": 0,
                "total_tokens": 0,
                "tokens_per_second": 0,
                "total_time": 0
            }  

    def create_dataset(self,
                       account_id: str,
                       dataset_id: str,
                       display_name: str,
                       api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new dataset in Fireworks AI before uploading data.
        
        Args:
            account_id: Fireworks account ID
            dataset_id: ID to assign to the new dataset
            display_name: Human-readable name for the dataset
            api_key: API key (defaults to the one used for initialization)
            
        Returns:
            Dictionary containing the API response
        """
        # Use the instance API key if none is provided
        api_key = api_key or self.api_key
        
        # Prepare the API endpoint URL
        url = f"https://api.fireworks.ai/v1/accounts/{account_id}/datasets"
        
        # Prepare headers with authentication
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Prepare the request payload
        payload = {
            "dataset": {
                "displayName": display_name,
                "userUploaded": {},
                "format": "FORMAT_UNSPECIFIED"
            },
            "datasetId": dataset_id
        }
        
        try:
            # Make the POST request to create the dataset
            response = requests.post(url, json=payload, headers=headers)
            
            # Check for successful response
            response.raise_for_status()
            
            # Return the parsed JSON response
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error creating dataset: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
            return {"error": str(e)}
    
    def upload_dataset(self, 
                      file_path: str, 
                      account_id: str, 
                      dataset_id: str, 
                      api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a dataset file to the Fireworks AI API.
        
        Args:
            file_path: Path to the file to upload
            account_id: Fireworks account ID
            dataset_id: ID of the dataset to upload to
            api_key: API key (defaults to the one used for initialization)
            
        Returns:
            Dictionary containing the API response
        """
        # Use the instance API key if none is provided
        api_key = api_key or self.api_key
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Prepare the API endpoint URL
        url = f"https://api.fireworks.ai/v1/accounts/{account_id}/datasets/{dataset_id}:upload"
        
        # Prepare headers with authentication
        headers = {
            "Authorization": f"Bearer {api_key}"
            # Don't set Content-Type here - requests will set it correctly with the boundary
        }
        
        try:
            # Open file in binary mode
            with open(file_path, 'rb') as file:
                # Create a dictionary with the file
                files = {
                    'file': (os.path.basename(file_path), file, 'application/octet-stream')
                }
                
                # Make the POST request with multipart/form-data
                response = requests.post(url, headers=headers, files=files)
                
                # Check for successful response
                response.raise_for_status()
                
                # Return the parsed JSON response
                return response.json()
                
        except requests.exceptions.RequestException as e:
            print(f"Error uploading dataset: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
            return {"error": str(e)}  