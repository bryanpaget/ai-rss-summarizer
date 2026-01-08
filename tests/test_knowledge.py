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


# =============================================================================
# Tests for Insight CRUD Operations (Subtask 1.2)
# =============================================================================


class TestSaveInsight:
    """Tests for KnowledgeBase.save_insight() method."""

    def test_save_insight_success(self, knowledge_base, sample_insight):
        """Test saving a new insight returns True."""
        result = knowledge_base.save_insight(sample_insight)
        assert result is True

    def test_save_insight_duplicate_fails(self, knowledge_base, sample_insight):
        """Test saving duplicate insight (same ID) returns False."""
        knowledge_base.save_insight(sample_insight)
        result = knowledge_base.save_insight(sample_insight)
        assert result is False

    def test_save_insight_persists_all_fields(self, knowledge_base, sample_insight):
        """Test that all insight fields are persisted correctly."""
        knowledge_base.save_insight(sample_insight)
        retrieved = knowledge_base.get_insight(sample_insight.id)

        assert retrieved is not None
        assert retrieved.id == sample_insight.id
        assert retrieved.article_id == sample_insight.article_id
        assert retrieved.content == sample_insight.content
        assert retrieved.insight_type == sample_insight.insight_type
        assert retrieved.confidence == sample_insight.confidence
        assert retrieved.confidence_reason == sample_insight.confidence_reason

    def test_save_insight_with_none_confidence_reason(self, knowledge_base):
        """Test saving insight with None confidence_reason."""
        insight = Insight(
            id="insight-no-reason",
            article_id="article-001",
            content="Test insight without confidence reason",
            insight_type="technical",
            confidence="medium",
            confidence_reason=None,
        )
        result = knowledge_base.save_insight(insight)
        assert result is True

        retrieved = knowledge_base.get_insight(insight.id)
        assert retrieved.confidence_reason is None

    def test_save_multiple_insights_same_article(self, knowledge_base):
        """Test saving multiple insights for the same article."""
        insight1 = Insight(
            id="multi-insight-001",
            article_id="article-shared",
            content="First insight",
            insight_type="technical",
            confidence="high",
        )
        insight2 = Insight(
            id="multi-insight-002",
            article_id="article-shared",
            content="Second insight",
            insight_type="opinion",
            confidence="low",
        )

        result1 = knowledge_base.save_insight(insight1)
        result2 = knowledge_base.save_insight(insight2)

        assert result1 is True
        assert result2 is True

        # Verify both exist
        assert knowledge_base.get_insight("multi-insight-001") is not None
        assert knowledge_base.get_insight("multi-insight-002") is not None


class TestGetInsight:
    """Tests for KnowledgeBase.get_insight() method."""

    def test_get_insight_existing(self, knowledge_base, sample_insight):
        """Test retrieving an existing insight by ID."""
        knowledge_base.save_insight(sample_insight)
        retrieved = knowledge_base.get_insight(sample_insight.id)

        assert retrieved is not None
        assert retrieved.id == sample_insight.id
        assert retrieved.content == sample_insight.content

    def test_get_insight_nonexistent(self, knowledge_base):
        """Test retrieving a non-existent insight returns None."""
        result = knowledge_base.get_insight("nonexistent-id")
        assert result is None

    def test_get_insight_empty_database(self, empty_knowledge_base):
        """Test retrieving from empty database returns None."""
        result = empty_knowledge_base.get_insight("any-id")
        assert result is None

    def test_get_insight_returns_correct_type(self, knowledge_base, sample_insight):
        """Test that get_insight returns an Insight object."""
        knowledge_base.save_insight(sample_insight)
        retrieved = knowledge_base.get_insight(sample_insight.id)

        assert isinstance(retrieved, Insight)

    def test_get_insight_extracted_at_populated(self, knowledge_base, sample_insight):
        """Test that extracted_at is populated after save."""
        knowledge_base.save_insight(sample_insight)
        retrieved = knowledge_base.get_insight(sample_insight.id)

        # extracted_at should be auto-populated by database
        assert retrieved.extracted_at is not None


class TestGetInsights:
    """Tests for KnowledgeBase.get_insights() method."""

    def test_get_insights_empty_database(self, empty_knowledge_base):
        """Test get_insights on empty database returns empty list."""
        result = empty_knowledge_base.get_insights()
        assert result == []

    def test_get_insights_returns_all(self, knowledge_base, sample_insights):
        """Test get_insights returns all saved insights."""
        for insight in sample_insights:
            knowledge_base.save_insight(insight)

        result = knowledge_base.get_insights()

        assert len(result) == len(sample_insights)

    def test_get_insights_limit(self, knowledge_base, sample_insights):
        """Test get_insights respects limit parameter."""
        for insight in sample_insights:
            knowledge_base.save_insight(insight)

        result = knowledge_base.get_insights(limit=2)

        assert len(result) == 2

    def test_get_insights_filter_by_type(self, knowledge_base, sample_insights):
        """Test filtering insights by insight_type."""
        for insight in sample_insights:
            knowledge_base.save_insight(insight)

        # Filter for 'technical' type
        technical_insights = knowledge_base.get_insights(insight_type="technical")

        assert len(technical_insights) == 1
        assert technical_insights[0].insight_type == "technical"

    def test_get_insights_filter_by_confidence(self, knowledge_base, sample_insights):
        """Test filtering insights by confidence level."""
        for insight in sample_insights:
            knowledge_base.save_insight(insight)

        # Filter for 'high' confidence
        high_confidence = knowledge_base.get_insights(confidence="high")

        assert len(high_confidence) == 2  # technical and statistic both have high confidence
        for insight in high_confidence:
            assert insight.confidence == "high"

    def test_get_insights_filter_by_article_id(self, knowledge_base, sample_insights):
        """Test filtering insights by article_id."""
        for insight in sample_insights:
            knowledge_base.save_insight(insight)

        # Filter for article-001 (should have technical and statistic insights)
        article_insights = knowledge_base.get_insights(article_id="article-001")

        assert len(article_insights) == 2
        for insight in article_insights:
            assert insight.article_id == "article-001"

    def test_get_insights_combined_filters(self, knowledge_base, sample_insights):
        """Test combining multiple filter parameters."""
        for insight in sample_insights:
            knowledge_base.save_insight(insight)

        # Filter for high confidence from article-001
        result = knowledge_base.get_insights(
            article_id="article-001",
            confidence="high"
        )

        assert len(result) == 2
        for insight in result:
            assert insight.article_id == "article-001"
            assert insight.confidence == "high"

    def test_get_insights_no_matches(self, knowledge_base, sample_insights):
        """Test get_insights returns empty list when no matches."""
        for insight in sample_insights:
            knowledge_base.save_insight(insight)

        result = knowledge_base.get_insights(insight_type="nonexistent_type")

        assert result == []

    def test_get_insights_filter_by_type_and_confidence(self, knowledge_base):
        """Test filtering by both type and confidence."""
        # Create specific test data
        insights = [
            Insight(id="test-001", article_id="a1", content="C1", insight_type="technical", confidence="high"),
            Insight(id="test-002", article_id="a2", content="C2", insight_type="technical", confidence="low"),
            Insight(id="test-003", article_id="a3", content="C3", insight_type="opinion", confidence="high"),
            Insight(id="test-004", article_id="a4", content="C4", insight_type="opinion", confidence="low"),
        ]

        for insight in insights:
            knowledge_base.save_insight(insight)

        # Filter for technical with high confidence
        result = knowledge_base.get_insights(insight_type="technical", confidence="high")

        assert len(result) == 1
        assert result[0].id == "test-001"
        assert result[0].insight_type == "technical"
        assert result[0].confidence == "high"

    def test_get_insights_default_limit(self, knowledge_base):
        """Test that default limit is 50."""
        # Create 60 insights
        for i in range(60):
            insight = Insight(
                id=f"limit-test-{i:03d}",
                article_id=f"article-{i}",
                content=f"Test content {i}",
                insight_type="technical",
                confidence="medium",
            )
            knowledge_base.save_insight(insight)

        result = knowledge_base.get_insights()

        # Default limit should be 50
        assert len(result) == 50

    def test_get_insights_ordered_by_extracted_at(self, knowledge_base):
        """Test that insights are ordered by extracted_at descending."""
        # Insert multiple insights
        insights_to_save = [
            Insight(id=f"order-{i:03d}", article_id=f"a{i}", content=f"Content {i}", insight_type="technical", confidence="high")
            for i in range(5)
        ]

        for insight in insights_to_save:
            knowledge_base.save_insight(insight)

        result = knowledge_base.get_insights()

        # Verify results are ordered by extracted_at descending (or at least have dates)
        assert len(result) == 5
        # Each result should have an extracted_at value
        for insight in result:
            assert insight.extracted_at is not None
        # Verify timestamps are in descending order (or equal if same second)
        for i in range(len(result) - 1):
            assert result[i].extracted_at >= result[i + 1].extracted_at

    def test_get_insights_returns_insight_objects(self, knowledge_base, sample_insight):
        """Test that get_insights returns list of Insight objects."""
        knowledge_base.save_insight(sample_insight)
        result = knowledge_base.get_insights()

        assert all(isinstance(insight, Insight) for insight in result)


class TestInsightIntegration:
    """Integration tests for insight operations."""

    def test_save_and_retrieve_multiple_types(self, knowledge_base):
        """Test saving and retrieving insights of different types."""
        types = ["technical", "tool", "statistic", "opinion"]

        for i, insight_type in enumerate(types):
            insight = Insight(
                id=f"type-test-{i}",
                article_id="article-001",
                content=f"Content for {insight_type}",
                insight_type=insight_type,
                confidence="medium",
            )
            knowledge_base.save_insight(insight)

        # Retrieve each type and verify
        for insight_type in types:
            result = knowledge_base.get_insights(insight_type=insight_type)
            assert len(result) == 1
            assert result[0].insight_type == insight_type

    def test_save_and_retrieve_different_confidence_levels(self, knowledge_base):
        """Test saving and retrieving insights with different confidence levels."""
        levels = ["high", "medium", "low"]

        for i, level in enumerate(levels):
            insight = Insight(
                id=f"conf-test-{i}",
                article_id="article-001",
                content=f"Content with {level} confidence",
                insight_type="technical",
                confidence=level,
            )
            knowledge_base.save_insight(insight)

        # Retrieve each level and verify
        for level in levels:
            result = knowledge_base.get_insights(confidence=level)
            assert len(result) == 1
            assert result[0].confidence == level

    def test_complex_query_scenario(self, knowledge_base):
        """Test a complex scenario with multiple articles and filters."""
        # Set up data: 3 articles, each with 2 insights of different types/confidence
        articles = ["article-A", "article-B", "article-C"]

        insight_id = 0
        for article_id in articles:
            # High confidence technical
            insight_id += 1
            knowledge_base.save_insight(Insight(
                id=f"complex-{insight_id}",
                article_id=article_id,
                content=f"Technical insight for {article_id}",
                insight_type="technical",
                confidence="high",
            ))

            # Low confidence opinion
            insight_id += 1
            knowledge_base.save_insight(Insight(
                id=f"complex-{insight_id}",
                article_id=article_id,
                content=f"Opinion for {article_id}",
                insight_type="opinion",
                confidence="low",
            ))

        # Test various queries
        # All insights
        all_insights = knowledge_base.get_insights()
        assert len(all_insights) == 6

        # All technical
        technical = knowledge_base.get_insights(insight_type="technical")
        assert len(technical) == 3

        # All high confidence
        high_conf = knowledge_base.get_insights(confidence="high")
        assert len(high_conf) == 3

        # Technical + high confidence
        tech_high = knowledge_base.get_insights(insight_type="technical", confidence="high")
        assert len(tech_high) == 3

        # Opinion + low confidence from article-A
        opinion_low_a = knowledge_base.get_insights(
            article_id="article-A",
            insight_type="opinion",
            confidence="low"
        )
        assert len(opinion_low_a) == 1
