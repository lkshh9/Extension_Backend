from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import groq
import os
import re
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend's domain for better security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load API key from environment variables
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")  # Set your Groq API key in .env file

# Initialize the Groq client
client = groq.Groq(api_key=api_key)

# Define comment syntax based on file extension
COMMENT_SYNTAX = {
    '.py': '#',      # Python
    '.js': '//',     # JavaScript
    '.ts': '//',     # TypeScript
    '.java': '//',   # Java
    '.c': '//',      # C
    '.cpp': '//',    # C++
    '.rb': '#',      # Ruby
    '.sh': '#',      # Shell scripts
    '.html': '<!--', # HTML
    '.css': '/*',    # CSS
}

# Input model for code snippet and file extension
class CodeSnippet(BaseModel):
    code: str = Field(..., min_length=10, description="Code snippet must be at least 10 characters long")
    file_extension: str = Field(..., description="File extension of the code snippet, e.g., .py, .js")

# Input model for docstring generation
class DocstringRequest(BaseModel):
    code: str = Field(..., min_length=10, description="Code snippet must be at least 10 characters long")
    format: str = Field(..., description="Docstring format, e.g., Google, NumPy, Sphinx")

@app.post("/generate-comment")
def generate_comments(snippet: CodeSnippet):
    try:
        comment_syntax = COMMENT_SYNTAX.get(snippet.file_extension, None)
        if not comment_syntax:
            raise HTTPException(status_code=400, detail="Unsupported file extension.")

        # Split code into lines and generate comments for each line
        code_lines = snippet.code.split('\n')
        comments = []  # List to store dynamically formatted comments for each line

        for line in code_lines:
            if line.strip():  # Skip empty lines
                # Using Groq API to generate a comment for each line
                chat_completion = client.chat.completions.create(
                    messages=[{
                        "role": "user",
                        "content": f"Write a single-line comment for this code:\n{line.strip()}",
                    }],
                    model="llama3-8b-8192",  # Adjust model if needed
                )

                # Extract raw comment text without comment syntax
                raw_text = chat_completion.choices[0].message.content.strip()
                match = re.search(r"^\s*(#\s*//?)?\s*(.+)", raw_text)

                if match:
                    # Extract the comment part
                    comment = match.group(2)  # The actual comment content without `# //`

                    # Apply your custom comment syntax (assuming comment_syntax is '#')
                    formatted_comment = f"{comment_syntax} {comment}"
                else:
                    formatted_comment = raw_text  # Fallback if no match is found

                # Append formatted comment
                comments.append(formatted_comment)
            else:
                comments.append("")  # Preserve empty lines

        return {"comments": comments}  # Return formatted comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
@app.post("/generate-docstring")
def generate_docstring(request: DocstringRequest):
    try:
        # Validate docstring format
        supported_formats = ["Google", "NumPy", "reST"]
        if request.format not in supported_formats:
            raise HTTPException(status_code=400, detail="Unsupported docstring format. Supported formats: Google, NumPy, Sphinx.")

        # Use Groq API to generate the docstring
        chat_completion = client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": f"Write a docstring in {request.format} format for the following code:\n{request.code}",
            }],
            model="llama3-8b-8192",  # Adjust model if needed
        )

        # Extract the generated docstring
        response_content = chat_completion.choices[0].message.content.strip()

        # Use regex to extract the docstring part from the response
        docstring_match = re.search(r'"""(.*?)"""', response_content, re.DOTALL)
        if docstring_match:
            docstring = f'"""{docstring_match.group(1).strip()}"""'
        else:
            # Fallback: Return the entire response if no docstring is found
            docstring = response_content

        return {"docstring": docstring}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# @app.get("/rate-limits")
# def get_rate_limits():
#     try:
#         # Retrieve rate-limit usage from Groq API
#         usage_info = client.usage.retrieve()

#         if not usage_info:
#             raise HTTPException(status_code=500, detail="Failed to retrieve usage information.")

#         return {
#             "remaining_requests": usage_info.remaining_requests,
#             "reset_time": usage_info.reset_time,
#             "total_tokens": usage_info.total_tokens,
#             "remaining_tokens": usage_info.remaining_tokens,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
