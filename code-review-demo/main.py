import openai
import os

def get_code_review(code):
    openai.api_key = os.environ.get("OPENAI_API_TOKEN")
    model_engine = "text-davinci-003"
    preprompt = ""
    with open("preprompt.txt", "r") as file:
        preprompt = file.read()

    prompt = f"{preprompt}\n{code}"

    completion = openai.Completion.create(
        engine=model_engine,
        prompt=prompt,
        max_tokens=1024,
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

    print(get_code_review(code))

if __name__ == "__main__":
    main()