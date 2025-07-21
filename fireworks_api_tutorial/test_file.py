from fireworks import LLM

# # Basic usage - SDK automatically selects optimal deployment type
# llm = LLM(model="llama4-maverick-instruct-basic", deployment_type="auto")

# response = llm.chat.completions.create(
#     messages=[{"role": "user", "content": "Say this is a test"}]
# )

# print(response.choices[0].message.content)


from fireworks import LLM

llm = LLM(
  model="qwen3-235b-a22b",
  deployment_type="serverless"
)
response = llm.chat.completions.create(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say this is a test"}
    ]
)
print(response.choices[0].message.content)