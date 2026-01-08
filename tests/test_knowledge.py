"""Tests for knowledge module."""

import os
import tempfile
from datetime import datetime

import pytest

from src.knowledge import (
    KnowledgeBase,
    Insight,
    Entity,
    Relationship,
    Triple,
    EntityRelationship,
    Embedding,
    UserContext,
)


# =============================================================================
# Fixtures for Database Setup
# =============================================================================


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def knowledge_base(temp_db):
    """Create a KnowledgeBase instance with temp database."""
    return KnowledgeBase(temp_db)


# =============================================================================
# Sample Data Fixtures - Insights
# =============================================================================


@pytest.fixture
def sample_insight():
    """Create a sample insight for testing."""
    return Insight(
        id="insight-001",
        article_id="article-001",
        content="Python 3.12 introduces significant performance improvements through optimized bytecode.",
        insight_type="technical",
        confidence="high",
        confidence_reason="Official Python documentation",
    )


@pytest.fixture
def sample_insight_low_confidence():
    """Create a low-confidence insight for testing."""
    return Insight(
        id="insight-002",
        article_id="article-002",
        content="AI will replace most programming jobs by 2030.",
        insight_type="opinion",
        confidence="low",
        confidence_reason="Speculation without data",
    )


@pytest.fixture
def sample_insight_statistic():
    """Create a statistic insight for testing."""
    return Insight(
        id="insight-003",
        article_id="article-001",
        content="Python is used by 48% of developers according to Stack Overflow survey.",
        insight_type="statistic",
        confidence="high",
        confidence_reason="Verified survey data from Stack Overflow 2024",
    )


@pytest.fixture
def sample_insights(sample_insight, sample_insight_low_confidence, sample_insight_statistic):
    """Create a list of sample insights for testing."""
    return [sample_insight, sample_insight_low_confidence, sample_insight_statistic]


# =============================================================================
# Sample Data Fixtures - Entities
# =============================================================================


@pytest.fixture
def sample_entity_tool():
    """Create a sample tool entity."""
    return Entity(
        id="entity-001",
        name="Python",
        entity_type="tool",
        mention_count=1,
    )


@pytest.fixture
def sample_entity_company():
    """Create a sample company entity."""
    return Entity(
        id="entity-002",
        name="OpenAI",
        entity_type="company",
        mention_count=1,
    )


@pytest.fixture
def sample_entity_person():
    """Create a sample person entity."""
    return Entity(
        id="entity-003",
        name="Guido van Rossum",
        entity_type="person",
        mention_count=1,
    )


@pytest.fixture
def sample_entity_concept():
    """Create a sample concept entity."""
    return Entity(
        id="entity-004",
        name="Machine Learning",
        entity_type="concept",
        mention_count=1,
    )


@pytest.fixture
def sample_entities(sample_entity_tool, sample_entity_company, sample_entity_person, sample_entity_concept):
    """Create a list of sample entities for testing."""
    return [sample_entity_tool, sample_entity_company, sample_entity_person, sample_entity_concept]


# =============================================================================
# Sample Data Fixtures - Triples (RDF-style)
# =============================================================================


@pytest.fixture
def sample_triple_developed_by():
    """Create a sample 'developed_by' triple."""
    return Triple(
        id="triple-001",
        subject="GPT-4",
        predicate="developed_by",
        object="OpenAI",
        subject_type="entity",
        object_type="entity",
        source_article_id="article-001",
        confidence="high",
    )


@pytest.fixture
def sample_triple_competes_with():
    """Create a sample 'competes_with' triple."""
    return Triple(
        id="triple-002",
        subject="OpenAI",
        predicate="competes_with",
        object="Anthropic",
        subject_type="entity",
        object_type="entity",
        source_article_id="article-002",
        confidence="high",
    )


@pytest.fixture
def sample_triple_created():
    """Create a sample 'created' triple."""
    return Triple(
        id="triple-003",
        subject="Guido van Rossum",
        predicate="created",
        object="Python",
        subject_type="entity",
        object_type="entity",
        source_article_id="article-003",
        confidence="high",
    )


@pytest.fixture
def sample_triple_literal():
    """Create a triple with literal object type."""
    return Triple(
        id="triple-004",
        subject="Python",
        predicate="released_version",
        object="3.12",
        subject_type="entity",
        object_type="literal",
        source_article_id="article-001",
        confidence="medium",
    )


@pytest.fixture
def sample_triples(sample_triple_developed_by, sample_triple_competes_with, sample_triple_created, sample_triple_literal):
    """Create a list of sample triples for testing."""
    return [sample_triple_developed_by, sample_triple_competes_with, sample_triple_created, sample_triple_literal]


# =============================================================================
# Sample Data Fixtures - Relationships (Insight-to-Insight)
# =============================================================================


@pytest.fixture
def sample_relationship_confirms():
    """Create a 'confirms' relationship between insights."""
    return Relationship(
        id="rel-001",
        source_insight_id="insight-001",
        target_insight_id="insight-003",
        relationship_type="confirms",
        strength=0.8,
    )


@pytest.fixture
def sample_relationship_contradicts():
    """Create a 'contradicts' relationship between insights."""
    return Relationship(
        id="rel-002",
        source_insight_id="insight-001",
        target_insight_id="insight-002",
        relationship_type="contradicts",
        strength=0.7,
    )


@pytest.fixture
def sample_relationship_extends():
    """Create an 'extends' relationship between insights."""
    return Relationship(
        id="rel-003",
        source_insight_id="insight-003",
        target_insight_id="insight-001",
        relationship_type="extends",
        strength=0.6,
    )


@pytest.fixture
def sample_relationships(sample_relationship_confirms, sample_relationship_contradicts, sample_relationship_extends):
    """Create a list of sample relationships for testing."""
    return [sample_relationship_confirms, sample_relationship_contradicts, sample_relationship_extends]


# =============================================================================
# Sample Data Fixtures - Entity Relationships
# =============================================================================


@pytest.fixture
def sample_entity_relationship_acquired():
    """Create an 'acquired' entity relationship."""
    return EntityRelationship(
        id="ent-rel-001",
        source_entity_id="entity-002",  # OpenAI
        target_entity_id="entity-005",
        relationship_type="acquired",
        properties='{"amount": "$10M", "year": "2023"}',
        source_article_id="article-001",
    )


@pytest.fixture
def sample_entity_relationship_founded():
    """Create a 'founded' entity relationship."""
    return EntityRelationship(
        id="ent-rel-002",
        source_entity_id="entity-003",  # Guido van Rossum
        target_entity_id="entity-001",  # Python
        relationship_type="created",
        properties='{"year": "1991"}',
        source_article_id="article-002",
    )


@pytest.fixture
def sample_entity_relationship_competes():
    """Create a 'competes_with' entity relationship."""
    return EntityRelationship(
        id="ent-rel-003",
        source_entity_id="entity-002",  # OpenAI
        target_entity_id="entity-006",
        relationship_type="competes_with",
        properties=None,
        source_article_id="article-003",
    )


@pytest.fixture
def sample_entity_relationships(sample_entity_relationship_acquired, sample_entity_relationship_founded, sample_entity_relationship_competes):
    """Create a list of sample entity relationships for testing."""
    return [sample_entity_relationship_acquired, sample_entity_relationship_founded, sample_entity_relationship_competes]


# =============================================================================
# Sample Data Fixtures - Embeddings
# =============================================================================


@pytest.fixture
def sample_embedding():
    """Create a sample embedding for testing."""
    # Simple mock vector as bytes
    mock_vector = bytes([0, 1, 2, 3, 4, 5, 6, 7, 8, 9] * 10)
    return Embedding(
        id="embed-001",
        target_id="insight-001",
        target_type="insight",
        vector=mock_vector,
        model="text-embedding-ada-002",
    )


@pytest.fixture
def sample_embedding_entity():
    """Create a sample entity embedding for testing."""
    mock_vector = bytes([10, 11, 12, 13, 14, 15, 16, 17, 18, 19] * 10)
    return Embedding(
        id="embed-002",
        target_id="entity-001",
        target_type="entity",
        vector=mock_vector,
        model="text-embedding-ada-002",
    )


@pytest.fixture
def sample_embeddings(sample_embedding, sample_embedding_entity):
    """Create a list of sample embeddings for testing."""
    return [sample_embedding, sample_embedding_entity]


# =============================================================================
# Sample Data Fixtures - User Context
# =============================================================================


@pytest.fixture
def sample_context_project():
    """Create a sample project context."""
    return UserContext(
        id="ctx-001",
        context_type="project",
        name="RSS Summarizer",
        description="Building an AI-powered RSS feed summarizer",
        active=True,
    )


@pytest.fixture
def sample_context_interest():
    """Create a sample interest context."""
    return UserContext(
        id="ctx-002",
        context_type="interest",
        name="Machine Learning",
        description="Following developments in ML and AI",
        active=True,
    )


@pytest.fixture
def sample_context_inactive():
    """Create an inactive context for testing filtering."""
    return UserContext(
        id="ctx-003",
        context_type="watching",
        name="Deprecated Tech",
        description="Old technology no longer of interest",
        active=False,
    )


@pytest.fixture
def sample_contexts(sample_context_project, sample_context_interest, sample_context_inactive):
    """Create a list of sample contexts for testing."""
    return [sample_context_project, sample_context_interest, sample_context_inactive]


# =============================================================================
# Graph Traversal Test Data - Complex Connected Graph
# =============================================================================


@pytest.fixture
def graph_triples():
    """Create a set of interconnected triples for graph traversal tests.

    Graph structure:
    OpenAI --developed--> GPT-4
    OpenAI --competes_with--> Anthropic
    Anthropic --developed--> Claude
    Microsoft --invested_in--> OpenAI
    Google --competes_with--> OpenAI
    Google --developed--> Gemini
    """
    return [
        Triple(
            id="graph-triple-001",
            subject="OpenAI",
            predicate="developed",
            object="GPT-4",
            subject_type="entity",
            object_type="entity",
            confidence="high",
        ),
        Triple(
            id="graph-triple-002",
            subject="OpenAI",
            predicate="competes_with",
            object="Anthropic",
            subject_type="entity",
            object_type="entity",
            confidence="high",
        ),
        Triple(
            id="graph-triple-003",
            subject="Anthropic",
            predicate="developed",
            object="Claude",
            subject_type="entity",
            object_type="entity",
            confidence="high",
        ),
        Triple(
            id="graph-triple-004",
            subject="Microsoft",
            predicate="invested_in",
            object="OpenAI",
            subject_type="entity",
            object_type="entity",
            confidence="high",
        ),
        Triple(
            id="graph-triple-005",
            subject="Google",
            predicate="competes_with",
            object="OpenAI",
            subject_type="entity",
            object_type="entity",
            confidence="medium",
        ),
        Triple(
            id="graph-triple-006",
            subject="Google",
            predicate="developed",
            object="Gemini",
            subject_type="entity",
            object_type="entity",
            confidence="high",
        ),
    ]


@pytest.fixture
def populated_knowledge_base(knowledge_base, graph_triples):
    """Create a knowledge base populated with graph triples for traversal tests."""
    for triple in graph_triples:
        knowledge_base.save_triple(triple)
    return knowledge_base


# =============================================================================
# Edge Case Fixtures
# =============================================================================


@pytest.fixture
def empty_knowledge_base(temp_db):
    """Create an empty knowledge base for edge case testing."""
    return KnowledgeBase(temp_db)


@pytest.fixture
def circular_graph_triples():
    """Create triples forming a circular reference.

    A --> B --> C --> A (circular)
    """
    return [
        Triple(
            id="circular-001",
            subject="EntityA",
            predicate="leads_to",
            object="EntityB",
            subject_type="entity",
            object_type="entity",
            confidence="high",
        ),
        Triple(
            id="circular-002",
            subject="EntityB",
            predicate="leads_to",
            object="EntityC",
            subject_type="entity",
            object_type="entity",
            confidence="high",
        ),
        Triple(
            id="circular-003",
            subject="EntityC",
            predicate="leads_to",
            object="EntityA",
            subject_type="entity",
            object_type="entity",
            confidence="high",
        ),
    ]
