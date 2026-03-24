from app.main import app

def test_read_root(client):
    # Simulating route "/"
    response = client.get("/")
    
    # Verify that it exists
    assert response.status_code == 200
    # Verify that it returns html file
    assert "text/html" in response.headers["content-type"]

def test_lifespan_loads_cedefop_data():
    # Checking if app.state has cedefop database
    assert hasattr(app.state, "cedefop")
    
    # Checking if it is not empty
    assert len(app.state.cedefop) > 0
    
    # Checking one of the keys
    assert "sectors" in app.state.cedefop