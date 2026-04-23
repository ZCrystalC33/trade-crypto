"""
LightRAG 文檔分析流程

從文檔攝入到查詢的完整流程管理
"""

import requests
import time
from typing import Dict, List, Optional
from datetime import datetime


class LightRAGAnalyzer:
    """
    LightRAG 文檔分析流程管理器
    
    流程：
    1. 攝入文檔（text/file）
    2. 等待處理完成
    3. 查詢分析
    4. 結果後處理
    """
    
    def __init__(self, base_url: str = "http://localhost:9621"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def is_ready(self) -> bool:
        """檢查服務是否就緒"""
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def ingest_text(self, text: str, file_name: str = None) -> Dict:
        """
        攝入文本
        
        Args:
            text: 文本內容
            file_name: 可選的文件名（便於追蹤）
        
        Returns:
            {"success": bool, "doc_id": str, "message": str}
        """
        try:
            resp = self.session.post(
                f"{self.base_url}/documents/text",
                json={"text": text},
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "doc_id": data.get("doc_id", ""),
                    "track_id": data.get("track_id", ""),
                    "message": f"Ingested: {file_name or 'text'}"
                }
            else:
                return {"success": False, "message": resp.text}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def ingest_file(self, file_path: str) -> Dict:
        """上傳文件（PDF, Markdown, TXT）"""
        try:
            with open(file_path, 'rb') as f:
                resp = self.session.post(
                    f"{self.base_url}/documents/file",
                    files={'file': f},
                    timeout=60
                )
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "doc_id": data.get("doc_id"),
                    "message": f"Uploaded: {file_path}"
                }
            else:
                return {"success": False, "message": resp.text}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def wait_for_processing(self, track_id: str = None, doc_id: str = None, timeout: int = 120, poll_interval: int = 5) -> bool:
        """
        等待文檔處理完成
        
        Args:
            track_id: 追蹤 ID（優先使用）
            doc_id: 文檔 ID
            timeout: 最大等待秒數
            poll_interval: 輪詢間隔
        
        Returns:
            True if processed, False if timeout
        """
        start = time.time()
        
        # 同時追蹤 track_id 和 doc_id
        while time.time() - start < timeout:
            try:
                params = {}
                if track_id:
                    params["track_id"] = track_id
                elif doc_id:
                    params["doc_id"] = doc_id
                else:
                    return False
                
                resp = self.session.get(
                    f"{self.base_url}/documents/pipeline_status",
                    params=params,
                    timeout=10
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # 檢查狀態 - 根據實際響應格式
                    if data.get("busy") == False:
                        return True
                    elif data.get("status") == "completed":
                        return True
                    elif data.get("latest_message") and "completed" in data.get("latest_message", "").lower():
                        return True
                
                time.sleep(poll_interval)
            except Exception as e:
                print(f"Poll error: {e}")
                time.sleep(poll_interval)
        
        return False
    
    def query(self, query_text: str, mode: str = "hybrid", top_k: int = 5) -> Dict:
        """
        查詢文檔
        
        Args:
            query_text: 查詢文本
            mode: "hybrid", "keyword", "vector"
            top_k: 返回結果數量
        
        Returns:
            {"success": bool, "results": [...], "message": str}
        """
        try:
            resp = self.session.post(
                f"{self.base_url}/query/{mode}",
                json={"query": query_text, "top_k": top_k},
                timeout=60
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "results": data.get("results", []),
                    "message": "Query successful"
                }
            else:
                return {"success": False, "message": resp.text}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def get_entities(self, limit: int = 50) -> List[Dict]:
        """取得所有實體"""
        try:
            resp = self.session.get(
                f"{self.base_url}/graphs",
                params={"label": "entity", "limit": limit},
                timeout=10
            )
            
            if resp.status_code == 200:
                return resp.json().get("entities", [])
            return []
        except:
            return []
    
    def get_relations(self, limit: int = 50) -> List[Dict]:
        """取得所有關係"""
        try:
            resp = self.session.get(
                f"{self.base_url}/graphs",
                params={"label": "relation", "limit": limit},
                timeout=10
            )
            
            if resp.status_code == 200:
                return resp.json().get("relations", [])
            return []
        except:
            return []
    
    def full_analysis_flow(self, text: str, query: str, file_name: str = None) -> Dict:
        """
        完整分析流程：攝入 → 等待 → 查詢
        
        Args:
            text: 文檔文本
            query: 查詢問題
            file_name: 文件名（可選）
        
        Returns:
            {"success": bool, "doc_id": str, "results": [...], "time_elapsed": float}
        """
        start = time.time()
        
        # 1. 攝入
        ingest_result = self.ingest_text(text, file_name)
        if not ingest_result["success"]:
            return {"success": False, "message": f"Ingest failed: {ingest_result['message']}"}
        
        track_id = ingest_result.get("track_id") or ingest_result.get("doc_id", "")
        
        # 2. 等待處理
        processed = self.wait_for_processing(track_id=track_id)
        if not processed:
            return {"success": False, "message": "Processing timeout"}
        
        # 3. 查詢
        query_result = self.query(query)
        
        elapsed = time.time() - start
        
        return {
            "success": query_result["success"],
            "doc_id": doc_id,
            "results": query_result.get("results", []),
            "time_elapsed": round(elapsed, 1)
        }


def create_analyzer() -> LightRAGAnalyzer:
    """工廠函數"""
    return LightRAGAnalyzer()
