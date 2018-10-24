
Documenting your API
--------------------

Each instance of Pulp optionally hosts dynamically generated API documentation located at
`http://pulpserver/pulp/api/v3/docs/`.

The API endpoint description is generated from the docstring on the CRUD methods on a ViewSet.

Individual parameters and responses are documented automatically based on the Serializer field type.
A field's description is generated from the "help_text" kwarg when defining serializer fields.

Response status codes can be generated through the `Meta` class on the serializer:

```
    from rest_framework.status import HTTP_400_BAD_REQUEST

    class SnippetSerializerV1(serializers.Serializer):
        title = serializers.CharField(required=False, allow_blank=True, max_length=100)

        class Meta:
            error_status_codes = {
                HTTP_400_BAD_REQUEST: 'Bad Request'
            }
```
