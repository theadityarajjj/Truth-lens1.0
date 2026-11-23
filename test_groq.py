from groq import Groq
from app.config import Config
import time


def test_groq():

    if not Config.GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY is missing.")
        return

    client = Groq(api_key=Config.GROQ_API_KEY)

    start = time.time()

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": "Is the Sun bigger than Earth? Answer briefly."
                }
            ],
            temperature=0.2
        )

        elapsed = time.time() - start

        print("\nGROQ CONNECTION SUCCESSFUL")
        print("Model:", response.model)
        print("Response:", response.choices[0].message.content)
        print("Time:", round(elapsed, 2), "seconds")

    except Exception as error:
        print("\nGROQ CONNECTION FAILED")
        print(type(error).__name__, str(error))


if __name__ == "__main__":
    test_groq()