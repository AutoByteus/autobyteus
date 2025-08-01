# gemini_api_examples.py

from google import genai
from google.genai import types
from PIL import Image

# Initialize Gemini client
client = genai.Client(api_key="GEMINI_API_KEY")

# 1. Basic text generation
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="How does AI work?"
)
print("Basic text generation:\n", response.text, end="\n\n")

# 2. Disable thinking
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="How does AI work?",
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )
)
print("With thinking disabled:\n", response.text, end="\n\n")

# 3. System instructions
response = client.models.generate_content(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction="You are a cat. Your name is Neko."
    ),
    contents="Hello there"
)
print("With system instruction:\n", response.text, end="\n\n")

# 4. Adjusting temperature
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=["Explain how AI works"],
    config=types.GenerateContentConfig(temperature=0.1)
)
print("With temperature 0.1:\n", response.text, end="\n\n")

# 5. Multimodal input with image
image = Image.open("/path/to/organ.png")
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[image, "Tell me about this instrument"]
)
print("With image input:\n", response.text, end="\n\n")

# 6. Streaming responses
response = client.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents=["Explain how AI works"]
)
print("Streaming response:")
for chunk in response:
    print(chunk.text, end="")
print("\n")

# 7. Multi-turn conversations (chat)
chat = client.chats.create(model="gemini-2.5-flash")
response = chat.send_message("I have 2 dogs in my house.")
print("Chat step 1:\n", response.text)

response = chat.send_message("How many paws are in my house?")
print("Chat step 2:\n", response.text)

print("\nChat history:")
for message in chat.get_history():
    print(f'{message.role}: {message.parts[0].text}')
    
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64

client = genai.Client()

contents = ('Hi, can you create a 3d rendered image of a pig '
            'with wings and a top hat flying over a happy '
            'futuristic scifi city with lots of greenery?')

response = client.models.generate_content(
    model="gemini-2.0-flash-preview-image-generation",
    contents=contents,
    config=types.GenerateContentConfig(
      response_modalities=['TEXT', 'IMAGE']
    )
)

for part in response.candidates[0].content.parts:
  if part.text is not None:
    print(part.text)
  elif part.inline_data is not None:
    image = Image.open(BytesIO((part.inline_data.data)))
    image.save('gemini-native-image.png')
    image.show()
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

import PIL.Image

image = PIL.Image.open('/path/to/image.png')

client = genai.Client()

text_input = ('Hi, This is a picture of me.'
            'Can you add a llama next to me?',)

response = client.models.generate_content(
    model="gemini-2.0-flash-preview-image-generation",
    contents=[text_input, image],
    config=types.GenerateContentConfig(
      response_modalities=['TEXT', 'IMAGE']
    )
)

for part in response.candidates[0].content.parts:
  if part.text is not None:
    print(part.text)
  elif part.inline_data is not None:
    image = Image.open(BytesIO(part.inline_data.data))
    image.show()
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

client = genai.Client(api_key='GEMINI_API_KEY')

response = client.models.generate_images(
    model='imagen-3.0-generate-002',
    prompt='Robot holding a red skateboard',
    config=types.GenerateImagesConfig(
        number_of_images= 4,
    )
)
for generated_image in response.generated_images:
  image = Image.open(BytesIO(generated_image.image.image_bytes))
  image.show()
import time
from google import genai
from google.genai import types

client = genai.Client()  # read API key from GOOGLE_API_KEY

operation = client.models.generate_videos(
    model="veo-2.0-generate-001",
    prompt="Panning wide shot of a calico kitten sleeping in the sunshine",
    config=types.GenerateVideosConfig(
        person_generation="dont_allow",  # "dont_allow" or "allow_adult"
        aspect_ratio="16:9",  # "16:9" or "9:16"
    ),
)

while not operation.done:
    time.sleep(20)
    operation = client.operations.get(operation)

for n, generated_video in enumerate(operation.response.generated_videos):
    client.files.download(file=generated_video.video)
    generated_video.video.save(f"video{n}.mp4")  # save the video
prompt="Panning wide shot of a calico kitten sleeping in the sunshine",

imagen = client.models.generate_images(
    model="imagen-3.0-generate-002",
    prompt=prompt,
    config=types.GenerateImagesConfig(
      aspect_ratio="16:9",
      number_of_images=1
    )
)

imagen.generated_images[0].image
operation = client.models.generate_videos(
    model="veo-2.0-generate-001",
    prompt=prompt,
    image = imagen.generated_images[0].image,
    config=types.GenerateVideosConfig(
      person_generation="dont_allow",  # "dont_allow" or "allow_adult"
      aspect_ratio="16:9",  # "16:9" or "9:16"
      number_of_videos=2
    ),
)

# Wait for videos to generate
 while not operation.done:
  time.sleep(20)
  operation = client.operations.get(operation)

for n, video in enumerate(operation.response.generated_videos):
    fname = f'with_image_input{n}.mp4'
    print(fname)
    client.files.download(file=video.video)
    video.video.save(fname)
