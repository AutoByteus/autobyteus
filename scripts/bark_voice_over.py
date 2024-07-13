# %%
## install bark pip install git+https://github.com/suno-ai/bark.git
from bark import SAMPLE_RATE, generate_audio, preload_models
from IPython.display import Audio

# download and load all models
preload_models(text_use_small=True)

# %%
# generate audio from text
text_prompt = """
     Hello, my name is Serpy. And, uh — and I like pizza. [laughs] 
     But I also have other interests such as playing tic tac toe.
"""
audio_array = generate_audio(text_prompt)

# play text in notebook
Audio(audio_array, rate=SAMPLE_RATE)


# %%
text_prompt = """
Ja, das Wort "zerstören" kommt aus dem Deutschen und bedeutet, etwas so zu beschädigen, dass es nicht mehr existiert oder nicht mehr in seinem ursprünglichen Zustand oder seiner ursprünglichen Form verwendet werden kann. Zerstören impliziert eine Handlung, die etwas vollständig kaputt macht, demoliert, vernichtet oder unbrauchbar macht. Dies kann sich auf physische Objekte beziehen, wie Gebäude, Brücken, Fahrzeuge oder Gegenstände, aber auch auf abstrakte Konzepte wie Beziehungen, Pläne oder Hoffnungen. Der Begriff kann in verschiedenen Kontexten verwendet werden, von tatsächlicher physischer Zerstörung bis hin zu metaphorischem Gebrauch, der den Verlust oder das Ende von etwas beschreibt.
"""
audio_array = generate_audio(text_prompt, output_full=True)
Audio(audio_array, rate=SAMPLE_RATE)

 #%%

# %%
import torch

# Check if CUDA (GPU support) is available
if torch.cuda.is_available():
    # Print the GPU name
    print(f"GPU available: {torch.cuda.get_device_name(0)}")
    
    # Create a tensor and move it to GPU
    tensor = torch.randn(3, 3).cuda()
    print("Tensor on GPU:", tensor)
    
    # Perform a simple computation on GPU
    result = tensor + tensor
    print("Result on GPU:", result)
    
else:
    print("CUDA is not available. No GPU detected or PyTorch is not installed with CUDA support.")


# %%

