from dictionaryutils import dictionary


def test_no_mixed_type_in_enum():
    for schema in dictionary.schema.values():
        for prop in schema["properties"].values():
            if "enum" in prop:
                assert all(
                    [type(i) == str for i in prop["enum"]]
                ), "{}: enum values should all be string".format(schema["id"])
