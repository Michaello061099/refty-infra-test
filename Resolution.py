# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, tempfile, shutil
import git
import yaml

app = FastAPI()

class UpdatePayload(BaseModel):
    image: str
    version: str

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_URL = "https://github.com/YOUR_USERNAME/refty-infra-test.git"
TARGET_IMAGE = "ghcr.io/refty-yapi/refty-node/refty-node"

@app.post("/update-image-version")
def update_image_version(payload: UpdatePayload):
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=500, detail="GitHub token not set")
    
    temp_dir = tempfile.mkdtemp()
    try:
        repo_url_with_token = REPO_URL.replace("https://", f"https://{GITHUB_TOKEN}@")
        repo = git.Repo.clone_from(repo_url_with_token, temp_dir)

        updated_files = []

        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith((".yaml", ".yml")):
                    full_path = os.path.join(root, file)
                    with open(full_path, 'r') as f:
                        content = f.read()
                    if payload.image in content:
                        new_content = content.replace(
                            f"{payload.image}:",
                            f"{payload.image}:{payload.version}"
                        )
                        if new_content != content:
                            with open(full_path, 'w') as f:
                                f.write(new_content)
                            updated_files.append(full_path)

        if not updated_files:
            raise HTTPException(status_code=404, detail="No files updated")

        repo.git.add(A=True)
        repo.index.commit(f"Update {payload.image} to version {payload.version}")
        origin = repo.remote(name='origin')
        origin.push()

        return {"message": "Update pushed", "files": updated_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(temp_dir)
