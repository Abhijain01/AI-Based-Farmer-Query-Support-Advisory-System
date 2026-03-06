from google import genai

# Pass the valid API key when creating the client
client = genai.Client(api_key="AIzaSyDG0PZuw6xFxzXjY2sz7A3-Luh3qs2cCbc")

response = client.models.generate_content(
    model="gemini-2.5-flash",  # pick a model your project has access to
    contents="Hello, world!"
)

print(response.text)
