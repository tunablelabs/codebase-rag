from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from git_parser.stats_docs_parser import RepoParser
# from git_parser.base_parser import CodeParser
from git_repo_parser.base_parser import CodeParser

router = APIRouter()

class RepoPath(BaseModel):
    path: str

@router.post("/stats")
async def analyze_repository(repo: RepoPath):
    try:
        parser = RepoParser(repo.path)
        return await parser.analyze_repository()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/analyze")
async def extract_repository(repo: RepoPath):
    try:
        parser = CodeParser()
        # This will trigger the full parsing logic including:
        # - Chunking through ChunkManager
        # - Relationship analysis
        # - Entity extraction
        results = parser.parse_directory(repo.path)
        # for file_path, entities in results.items():
        #     print(f"\nFile: {file_path}")
        #     for entity in entities:
        #         print(f"- {entity.type}: {entity.name}")
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))