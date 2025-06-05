from .base_model import BaseModel
from mongoengine import *
from datetime import datetime

# Embedded document classes for nested structures
class SamplingParameters(EmbeddedDocument):
    temperature_range = ListField(FloatField(), required=True)
    top_p = FloatField(required=True)

class PromptStructure(EmbeddedDocument):
    user_prompt_template = StringField(required=True)
    language_style = StringField()

class AdvancedOptions(EmbeddedDocument):
    strict_mode = BooleanField(default=True)

class DatasetParameters(EmbeddedDocument):
    output_format = StringField(required=True)
    task_description = StringField(required=True)
    max_tokens = IntField(required=True)
    seed_value = IntField(required=True)
    validation_rules = ListField(StringField())

class ResponseValidation(EmbeddedDocument):
    min_length = IntField()
    max_length = IntField()
    required_elements = ListField(StringField())
    forbidden_elements = ListField(StringField())

class DiversityControls(EmbeddedDocument):
    min_unique_words = IntField()
    max_repetition = FloatField()
    style_variation = FloatField()

class ConsistencyChecks(EmbeddedDocument):
    context_window = IntField()
    style_consistency = FloatField()
    fact_consistency = FloatField()

class QualityControls(EmbeddedDocument):
    response_validation = EmbeddedDocumentField(ResponseValidation)
    diversity_controls = EmbeddedDocumentField(DiversityControls)
    consistency_checks = EmbeddedDocumentField(ConsistencyChecks)

class VariationControls(EmbeddedDocument):
    temperature_variation = FloatField()
    style_variation = FloatField()
    complexity_variation = FloatField()

class SamplingStrategy(EmbeddedDocument):
    method = StringField()
    min_unique_ratio = FloatField()
    max_similarity = FloatField()

class ContentBalancing(EmbeddedDocument):
    topic_distribution = StringField()
    difficulty_levels = ListField(StringField())
    style_distribution = ListField(StringField())

class DiversityParameters(EmbeddedDocument):
    variation_controls = EmbeddedDocumentField(VariationControls)
    sampling_strategy = EmbeddedDocumentField(SamplingStrategy)
    content_balancing = EmbeddedDocumentField(ContentBalancing)

class QualityMetrics(EmbeddedDocument):
    coherence_score = FloatField()
    relevance_score = FloatField()
    completeness_score = FloatField()

class DiversityMetrics(EmbeddedDocument):
    vocabulary_richness = FloatField()
    syntactic_diversity = FloatField()
    semantic_diversity = FloatField()

class ConsistencyMetrics(EmbeddedDocument):
    factual_accuracy = FloatField()
    style_consistency = FloatField()
    context_relevance = FloatField()

class EvaluationMetrics(EmbeddedDocument):
    quality_metrics = EmbeddedDocumentField(QualityMetrics)
    diversity_metrics = EmbeddedDocumentField(DiversityMetrics)
    consistency_metrics = EmbeddedDocumentField(ConsistencyMetrics)

class YAMLConfig(BaseModel):
    # Basic metadata
    name = StringField(required=True)
    created_at = DateTimeField(default=datetime.now)
    
    # Top-level fields from the YAML examples
    # Legacy fields kept for backward compatibility
    number_of_samples = IntField(required=True)
    model = StringField(required=False, default="gpt-4o-mini")
    user_prompt = StringField(required=True)  # Keep for backward compatibility
    
    # New nested structure from examples
    sampling_parameters = EmbeddedDocumentField(SamplingParameters)
    prompt_structure = EmbeddedDocumentField(PromptStructure)
    required_criteria = ListField(StringField(), required=True)
    advanced_options = EmbeddedDocumentField(AdvancedOptions)
    dataset_parameters = EmbeddedDocumentField(DatasetParameters)
    quality_controls = EmbeddedDocumentField(QualityControls)
    diversity_parameters = EmbeddedDocumentField(DiversityParameters)
    evaluation_metrics = EmbeddedDocumentField(EvaluationMetrics)
    example_inputs = ListField(StringField())
    
    # Dataset upload fields
    dataset_id = StringField()  # ID of the dataset in Fireworks AI
    dataset_uploaded = BooleanField(default=False)  # Flag to track upload status
    dataset_upload_response = DictField()  # Response from the upload API
    
    # Performance Metrics - Storing sums for atomic updates
    total_responses_generated = IntField(default=0)
    tokens_per_second_sum = FloatField(default=0.0)  # Sum of TPS 
    time_to_first_token_sum = FloatField(default=0.0)  # Sum of TTFT in ms
    queries_per_second_sum = FloatField(default=0.0)  # Sum of QPS
    average_latency_sum = FloatField(default=0.0)  # Sum of latency in ms
    total_tokens_sum = IntField(default=0)  # Sum of tokens generated

    # Raw YAML content for reference
    raw_yaml = StringField(required=True)
    
    meta = {
        'collection': 'yaml_configs',
        'indexes': [
            'created_at',
            'name',
            'model'
        ]
    }
    
    # Properties to calculate averages dynamically
    @property
    def tokens_per_second(self):
        if self.total_responses_generated > 0:
            return self.tokens_per_second_sum / self.total_responses_generated
        return 0.0
    
    @property
    def time_to_first_token(self):
        if self.total_responses_generated > 0:
            return self.time_to_first_token_sum / self.total_responses_generated
        return 0.0
    
    @property
    def queries_per_second(self):
        if self.total_responses_generated > 0:
            return self.queries_per_second_sum / self.total_responses_generated
        return 0.0
    
    @property
    def average_latency(self):
        if self.total_responses_generated > 0:
            return self.average_latency_sum / self.total_responses_generated
        return 0.0
    
    @property
    def average_tokens(self):
        if self.total_responses_generated > 0:
            return self.total_tokens_sum / self.total_responses_generated
        return 0
    
    # Backward compatibility methods for accessing nested fields
    @property
    def temperature_range(self):
        if self.sampling_parameters:
            return self.sampling_parameters.temperature_range
        return None
    
    @property
    def top_p(self):
        if self.sampling_parameters:
            return self.sampling_parameters.top_p
        return None
    
    @property
    def strict_mode(self):
        if self.advanced_options:
            return self.advanced_options.strict_mode
        return True  # Default value
    
    @property
    def output_format(self):
        if self.dataset_parameters:
            return self.dataset_parameters.output_format
        return None
    
    @property
    def task_description(self):
        if self.dataset_parameters:
            return self.dataset_parameters.task_description
        return None
    
    @property
    def max_tokens(self):
        if self.dataset_parameters:
            return self.dataset_parameters.max_tokens
        return None
    
    @property
    def seed_value(self):
        if self.dataset_parameters:
            return self.dataset_parameters.seed_value
        return None
    
    @property
    def validation_rules(self):
        if self.dataset_parameters:
            return self.dataset_parameters.validation_rules
        return [] 