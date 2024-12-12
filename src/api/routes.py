from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from git_parser.stats_docs_parser import RepoParser
from git_parser.base_parser import CodeParser

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
        # print(results)
        
        # formatted_results = {
        #     "repo_path": repo.path,
        #     "files_analyzed": len(results),
        #     "analysis_results": {
        #         file_path: {
        #             "chunks": result.get('chunks', []),
        #             "total_chunks": len(result.get('chunks', [])),
        #             "file_path": file_path
        #         }
        #         for file_path, result in results.items()
        #     }
        # }
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))