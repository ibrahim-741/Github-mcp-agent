import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Model IDs verified at https://developers.openai.com
# gpt-5.4-mini = best cost/quality for coding + tool calling
# gpt-5.4      = flagship, use when you need maximum reasoning
# gpt-5.4-nano = ultra-cheap fallback, less reliable for agent loops
DEFAULT_MODEL = "gpt-5.4-mini" #for better response
DEFAULT_TEMPERATURE = 0.1


def get_llm(model: str | None = None,temperature: float | None = None) -> ChatOpenAI:
    """Return a configured ChatOpenAI client.

    Resolution order for each setting:
        explicit argument  ->  environment variable  ->  default constant
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found. Set it in your .env file.")

    resolved_model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL

    resolved_temp = temperature
    if resolved_temp is None:
        raw_temp = os.getenv("OPENAI_TEMPERATURE")
        resolved_temp = float(raw_temp) if raw_temp else DEFAULT_TEMPERATURE

    return ChatOpenAI(
        model=resolved_model,
        temperature=resolved_temp,
        max_retries=2,
    )


if __name__ == '__main__':
    chat_model = get_llm()

    response = chat_model.invoke("Tell me about MacBook M2 Air speciality and why it is still best in 2026.")
    print(response.content)

    


