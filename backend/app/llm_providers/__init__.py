# LLM 공급자 어댑터. 각 모듈은 공급자 SDK 호출을 `app.llm.LLMClient`로 감싼다.
# 어느 어댑터를 쓸지는 `app.settings.get_llm_client()`가 LLM_PROVIDER로 고른다.
