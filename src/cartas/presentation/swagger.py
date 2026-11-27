from flask import Blueprint, Response, send_from_directory

swagger = Blueprint("swagger", __name__)


@swagger.get("/openapi.json")
def especificacao_openapi() -> Response:
    return send_from_directory(swagger.root_path, "openapi.json")


@swagger.get("/docs")
def interface_swagger() -> str:
    return """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Distribuição de Cartas — Swagger UI</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({
      url: './openapi.json',
      dom_id: '#swagger-ui',
      validatorUrl: null,
    });
  </script>
</body>
</html>
"""
