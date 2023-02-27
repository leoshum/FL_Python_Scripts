import openai
import tiktoken
import os

class CodeReviewProvider:
    def __init__(self):
        openai.api_key = os.environ.get("OPENAI_API_TOKEN")
        with open("preprompt.txt", "r") as file:
            self.prepromt = file.read()

    def get_code_review(self, code):
        model_engine = "text-davinci-003"
        prompt = f"{self.prepromt}\n{code}"
        encoding = tiktoken.get_encoding("p50k_base")
        max_tokens = 4097 - len(encoding.encode(prompt))
        if max_tokens < 0:
            max_tokens = 4097
        completion = openai.Completion.create(
            engine=model_engine,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.5,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return completion.choices[0].text

def main():
    code = ""
    with open("code-sample.txt", "r") as file:
        code = file.read()

    code_review = CodeReviewProvider()
    print(code_review.get_code_review(code))
if __name__ == "__main__":
    main()