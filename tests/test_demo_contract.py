import importlib
from fastapi.testclient import TestClient
import backend.main as main
import parse_captions

def test_import_parser_does_not_modify_catalog():
    path = parse_captions.OUTPUT
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    importlib.reload(parse_captions)
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before

def test_demo_search_and_empty_result():
    client = TestClient(main.app)
    response = client.post('/api/search', json={'query':'cotton','limit':10})
    assert response.status_code == 200
    assert response.json()['count'] == 3
    assert client.post('/api/search', json={'query':'not-in-the-demo'}).json()['results'] == []
    assert client.get('/api/health').json()['products'] == 6
    assert 'fictional products' in client.get('/').text

def test_xml_special_characters_are_escaped():
    import xml.etree.ElementTree as ET
    response = main.build_twiml_message('Cotton & silk <sale>')
    assert ET.fromstring(response.body).find('Message').text == 'Cotton & silk <sale>'

def test_search_rejects_oversized_query():
    assert TestClient(main.app).post('/api/search', json={'query':'x'*201}).status_code == 422
