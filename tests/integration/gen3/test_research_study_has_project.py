
def test_research_study_has_project(distribution_schema: dict):
    """Ensure there is a link between ResearchSubject and Project"""
    assert "research_study.yaml" in distribution_schema
    research_study = distribution_schema["research_study.yaml"]
    assert "_project.yaml" in distribution_schema
    link_labels = [_['label'] for _ in research_study['links']]
    assert 'ResearchStudy_gen3_project_Project_research_study' in link_labels, link_labels
    assert '_project' not in research_study['properties']
