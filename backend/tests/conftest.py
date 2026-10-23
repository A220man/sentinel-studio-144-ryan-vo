import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch
import tempfile
import os

# Set test database URL BEFORE importing app modules
TEST_DB_FILE = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_FILE.close()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE.name}"
os.environ["SECRET_KEY"] = "test-secret-key-min-32-characters-long"
os.environ["KEYCLOAK_URL"] = "http://localhost:8080"
os.environ["KEYCLOAK_REALM"] = "test"
os.environ["KEYCLOAK_CLIENT_ID"] = "test-client"
os.environ["KEYCLOAK_CLIENT_SECRET"] = "test-secret"
os.environ["KEYCLOAK_REDIRECT_URI"] = "http://localhost:8000/auth/callback"
os.environ["DEBUG"] = "true"

from app.main import create_app
from app.core.database import Base, get_async_session, engine as app_engine
from app.core.config import settings
from app.models import User, UserRole

TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE.name}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session")
async def test_app():
    """Create test FastAPI app."""
    app = create_app()
    yield app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    """Initialize test database once per session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()
    # Clean up temp file
    try:
        os.unlink(TEST_DB_FILE.name)
    except OSError:
        pass


@pytest_asyncio.fixture
async def db_session():
    """Create a fresh database session for each test."""
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_app, db_session):
    """Create test client with overridden database dependency."""
    def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_async_session] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac

    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    import uuid
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        keycloak_sub=f"test-sub-{unique_suffix}",
        email=f"test{unique_suffix}@example.com",
        username=f"testuser{unique_suffix}",
        full_name="Test User",
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Generate auth headers for test user."""
    from app.core.security import create_access_token
    token = create_access_token({"sub": str(test_user.id), "email": test_user.email, "username": test_user.username, "roles": [test_user.role.value]})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_headers_with_csrf(test_user):
    """Generate auth headers with CSRF token for mutating requests."""
    from app.core.security import create_access_token, generate_csrf_token, hash_csrf_token
    token = create_access_token({"sub": str(test_user.id), "email": test_user.email, "username": test_user.username, "roles": [test_user.role.value]})
    csrf_token = generate_csrf_token()
    return {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": csrf_token,
        "Cookie": f"csrf_token={hash_csrf_token(csrf_token)}"
    }


@pytest.fixture(autouse=True)
def mock_keycloak_methods():
    """Mock KeycloakAuth methods to avoid external HTTP calls."""
    with patch("app.core.auth.KeycloakAuth.build_auth_url") as mock_build_auth, \
         patch("app.core.auth.KeycloakAuth.exchange_code_for_tokens") as mock_exchange, \
         patch("app.core.auth.KeycloakAuth.get_userinfo") as mock_userinfo, \
         patch("app.core.auth.KeycloakAuth.get_jwks") as mock_jwks, \
         patch("app.core.auth.KeycloakAuth.verify_id_token") as mock_verify:

        mock_build_auth.return_value = "http://keycloak/auth?state=test&code_challenge=test"
        mock_exchange.return_value = {
            "access_token": "kc-access-token",
            "id_token": "kc-id-token",
            "refresh_token": "kc-refresh-token",
        }
        mock_userinfo.return_value = {
            "sub": "test-sub-123",
            "email": "test@example.com",
            "preferred_username": "testuser",
            "name": "Test User",
            "picture": None,
        }
        mock_jwks.return_value = {"keys": []}
        mock_verify.return_value = {
            "sub": "test-sub-123",
            "email": "test@example.com",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["viewer"]},
        }

        yield {
            "build_auth_url": mock_build_auth,
            "exchange_code_for_tokens": mock_exchange,
            "get_userinfo": mock_userinfo,
            "get_jwks": mock_jwks,
            "verify_id_token": mock_verify,
        }