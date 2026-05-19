def test_token_wrapper_imports_quota_helper():
    from qwenpaw.enterprise.quota.llm import consume_llm_tokens

    assert callable(consume_llm_tokens)
