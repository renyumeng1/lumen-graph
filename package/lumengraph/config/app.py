from __future__ import annotations


import os
from pathlib import Path

import tomli
import tomli_w
from typing import Any


from pydantic import BaseModel,Field,PrivateAttr


class Config(BaseModel):
    
    
    save_dir:str = Field(default="saves",description="保存目录")
    app_name:str = Field(default="lumengraph-backend",description="应用名称")
    app_env: str = Field(default="development", description="运行环境")
    
    # ============== 模型相关配置 ==============
    default_model: str = Field(
        default="siliconflow-cn:Pro/MiniMaxAI/MiniMax-M2.5",
        description="默认对话模型",
    )
    fast_model: str = Field(
        default="siliconflow-cn:Pro/MiniMaxAI/MiniMax-M2.5",
        description="快速响应模型",
    )
    embed_model: str = Field(
        default="siliconflow-cn:Pro/BAAI/bge-m3",
        description="默认 Embedding 模型",
    )
    reranker: str = Field(
        default="siliconflow-cn:Pro/BAAI/bge-reranker-v2-m3",
        description="默认 Re-Ranker 模型",
    )
    content_guard_llm_model: str = Field(
        default="siliconflow-cn:Pro/MiniMaxAI/MiniMax-M2.5",
        description="内容审查LLM模型",
    )
    
    # ============== 智能体相关配置 ==============
    default_agent_id:str = Field(default="ChatbotAgent",description="默认智能体ID")
    
    # ============== 沙箱相关配置 ==============
    sandbox_provider:str = Field(default="provisioner", description="沙箱提供者")
    sandbox_provisioner_url: str = Field(default="http://sandbox-provisioner:8002", description="沙箱服务地址")
    sandbox_virtual_path_prefix: str = Field(default="/home/gem/user-data", description="沙箱用户目录前缀")
    sandbox_exec_timeout_seconds: int = Field(default=180, description="沙箱执行超时时间（秒）")
    sandbox_max_output_bytes: int = Field(default=262144, description="沙箱最大输出字节数")
    sandbox_keepalive_interval_seconds: int = Field(default=30, description="沙箱保活间隔（秒）")
    
    
    _config_file:Path | None = PrivateAttr(default=None)
    _user_modified_fields:set[str] = PrivateAttr(default_factory=set)
    
    
    model_config = {
        "arbitrary_types_allowed":True,
        "extra":"allow"
    }
    
    
    def __init__(self, **data:Any) -> None:
        super().__init__(**data)
        self._setup_paths()
        self._load_user_config()
        self._handle_environment()
        
        
    def _setup_paths(self):
        """"设置用户配置文件路径，并允许 SAVE_DIR 覆盖默认保存目录"""
        self.save_dir = os.getenv("SAVE_DIR", self.save_dir)
        self._config_file = Path(self.save_dir) / "config" / "base.toml"
        
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        
    
    
    def _load_user_config(self):
        """从 TOML 加载用户改过的配置项；位置字段跳过，避免旧配置阻塞启动。"""
        if not self._config_file or not self._config_file.exists():
            return
        
        with open(self._config_file,"rb") as f:
            user_config = tomli.load(f)
            self._user_modified_fields = set(user_config.keys())
            for key,value in user_config.items():
                if hasattr(self,key):
                    setattr(self,key,value)
                    
                    
    def _handle_environment(self):
        self.sandbox_provider = (os.getenv("SANDBOX_PROVIDER") or self.sandbox_provider).strip()
        self.sandbox_provisioner_url = (os.getenv("SANDBOX_PROVISIONER_URL") or self.sandbox_provisioner_url).strip()
        self.sandbox_virtual_path_prefix = (
        os.getenv("SANDBOX_VIRTUAL_PATH_PREFIX") or self.sandbox_virtual_path_prefix
    ).strip()
        self.sandbox_exec_timeout_seconds = int(
            os.getenv("SANDBOX_EXEC_TIMEOUT_SECONDS") or self.sandbox_exec_timeout_seconds
        )
        self.sandbox_max_output_bytes = int(os.getenv("SANDBOX_MAX_OUTPUT_BYTES") or self.sandbox_max_output_bytes)
        self.sandbox_keepalive_interval_seconds = int(
            os.getenv("SANDBOX_KEEPALIVE_INTERVAL_SECONDS") or self.sandbox_keepalive_interval_seconds
        )
        
        if self.sandbox_provider.lower() != "provisioner":
            raise ValueError("Only sandbox_provider=provisioner is supported.")
        if not self.sandbox_provisioner_url:
            raise ValueError("SANDBOX_PROVISIONER_URL is required when sandbox provider is provisioner.")
        if not self.sandbox_virtual_path_prefix.startswith("/"):
            self.sandbox_virtual_path_prefix = f"/{self.sandbox_virtual_path_prefix}"
                    
                    
    
    def save(self):
        """只保存偏离代码默认值的配置，避免把运行时状态写入 TOML"""
        if not self._config_file:
            return 
        
        default_config = Config.model_construct()
        
        user_modified = {}
        
        for field_name,field_info in Config.model_fields.items():
            if field_info.exclude:
                continue
            current_value = getattr(self,field_name)
            default_value = getattr(default_config,field_name)
            
            if current_value != default_value:
                user_modified[field_name] = current_value
                
        with open(self._config_file,"wb") as f:
            tomli_w.dump(user_modified,f)
            
    def dump_config(self)->dict[str,Any]:
        """导出给 `/api/system/config` 使用的配置和字段元数据。"""
        config_dict = self.model_dump()
        config_dict["config_items"] = {
            name: {
                "des": field.description,
                "default": field.default,
                "type": getattr(field.annotation, "__name__", str(field.annotation)), # 这里是有__future__的话field.annotation是个str所有直接用他的字符串没有的话再用__name__
                "exclude": bool(field.exclude),
            }
            for name, field in Config.model_fields.items()
            if not field.exclude
        }
        
        return config_dict
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def __setitem__(self, key, value):
        setattr(self, key, value)
    
    def update(self,other:dict[str,Any]):
        for key,value in other.items():
            if hasattr(self,key):
                setattr(self,key,value)
        
config = Config()  
    
    