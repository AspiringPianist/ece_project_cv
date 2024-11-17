from together import Together

client = Together(api_key="f79744841a9d211621a12f924b810dab2a71a48375b78a094372fb9ae3c9fbe6")

response = client.chat.completions.create(
    model="meta-llama/Meta-Llama-Guard-3-8B",
    messages=[{"role": "user", "content": "" }],
)
print(response.choices[0].message.content)