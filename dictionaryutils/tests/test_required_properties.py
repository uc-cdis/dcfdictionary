from dictionaryutils import dictionary


def test_required_program_property():
    required = "dbgap_accession_number"
    schema = dictionary.schema["program"]
    assert "required" in schema, (
                "No required properties defined in a program node")
    assert required in schema["required"], (
                "{} is required property for a program node, but not defined "
                "as required".format(required))


def test_required_project_property():
    required = "dbgap_accession_number"
    schema = dictionary.schema["project"]
    assert "required" in schema, (
                "No required properties defined in a project node")
    assert required in schema["required"], (
                "{} is required property for a project node, but not defined "
                "as required".format(required))


def test_required_ubiquitous_properties():
    required = ["submitter_id", "type"]
    for schema in dictionary.schema.values():
        if (
            not schema["id"] in ("program", "project")
            and not schema["category"] == "internal"
        ):
            assert "required" in schema, (
                    "No required properties defined in a {} "
                    "node".format(schema["id"]))
            for property in required:
                assert property in schema["required"], (
                    "{} is required property for a {} node, but not defined "
                    "as required".format(property, schema["id"]))


def test_required_internal_properties():
    required = "type"
    for schema in dictionary.schema.values():
        if schema["category"] == "internal":
            assert "required" in schema, (
                    "No required properties defined in a {} "
                    "node".format(schema["id"]))
            assert required in schema["required"], (
                    "{} is required property for a {} node, but not defined "
                    "as required".format(required, schema["id"]))
