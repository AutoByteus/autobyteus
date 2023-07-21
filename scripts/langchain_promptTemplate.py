# %%
from langchain import PromptTemplate

# An example prompt with multiple input variables
multiple_input_prompt = PromptTemplate(
 input_variables=["adjective", "content"], 
 template="Tell me a {adjective} joke about {content}."
)

multiple_input_prompt.format(adjective="funny", content="chickens")
# -> "Tell me a funny joke about chickens."

# %%
from langchain import PromptTemplate

# An example prompt with multiple input variables
multiple_input_prompt = PromptTemplate(
 input_variables=["adjective", "content"], 
 template="Tell me a {adjective} joke about {content}."
)

multiple_input_prompt.format(adjective="funny", content="chickens")
# -> "Tell me a funny joke about chickens."

# %%
