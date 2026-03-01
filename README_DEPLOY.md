# Deploy do Backend

Este documento mostra os passos necessários para colocar o backend em produção.

## 1. Preparar o ambiente

1. Clonar o repositório no servidor ou serviço de deploy (Heroku, Render, etc.).
2. Criar virtualenv e instalar dependências:

```bash
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate.ps1 no Windows
pip install -r requirements.txt
```

3. Configurar variáveis de ambiente:

```bash
export DJANGO_SECRET_KEY="chave_super_segura"
export DJANGO_DEBUG=False
export DJANGO_ALLOWED_HOSTS="seusite.com"
export DOCTOR_EMAIL="doutora@exemplo.com"
export FIREBASE_CREDENTIALS_PATH="/caminho/para/credentials.json"
# opcional: DATABASE_URL para PostgreSQL
```

## 2. Configuração do Django

- `settings.py` já lê `DJANGO_*` e usa WhiteNoise.
- Para migrar:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
``` 

- Criar usuário administrador (psicóloga) se necessário:

```bash
python manage.py createsuperuser
# ou use o shell para definir is_staff=True
``` 

## 3. Arquivo Procfile

Aplicações como Heroku/Render usam o `Procfile` fornecido:

```
web: gunicorn backend.wsgi --log-file -
```

## 4. Deploy em serviços comuns

### Heroku

```bash
heroku create nome-app
heroku config:set DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" ...
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py collectstatic --noinput
``` 

### Render / DigitalOcean App

- Escolha Python, aponte para o repositório Git.
- Defina "Build Command" como `pip install -r requirements.txt`.
- Defina "Start Command" como `gunicorn backend.wsgi`.
- Configure variáveis de ambiente como acima.

## 5. SSL / HTTPS

Serviços já fornecem certificado. Em VPS, instale e configure nginx + certbot.

## 6. Verificar funcionamento

- Visite `https://seusite.com/api/token-auth/` (deve retornar 400 POST). 
- Teste endpoints com `curl` ou Postman.

## 7. Atualizar Flutter

- No Flutter, aponte `ApiService._baseUrl` para a URL pública.
- Recompile em modo release.


Este guia se destina a um ambiente de produção; para testes locais podem manter `DEBUG=True` e `ALLOWED_HOSTS=['*']`.
