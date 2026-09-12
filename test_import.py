import sys
sys.path.append(r'd:/SMART_EDUCATION_ASSISTANT')
try:
    import modules.metadata as m
    print('OK', hasattr(m, 'save_chunks'), hasattr(m, 'load_chunks'))
except Exception as e:
    print('ERROR', e)
