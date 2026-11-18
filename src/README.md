# API de Atividades da Mergington High School

Uma aplicação FastAPI que permite visualizar atividades extracurriculares e aos professores gerenciar inscrições.

## Funcionalidades

- Visualizar todas as atividades extracurriculares disponíveis
- Professores autenticados podem inscrever e remover estudantes
- Estudantes sem login podem visualizar atividades e participantes

## Primeiros Passos

1. Instale as dependências:

   ```
   pip install fastapi uvicorn
   ```

2. Na pasta `src`, crie um usuário de professor:

   ```
   python auth.py NOME_DE_USUARIO
   ```

   Digite e confirme a senha quando solicitado. O arquivo local `teachers.json`
   armazena hashes com salt, não senhas em texto puro, e não deve ser enviado ao
   repositório. Repita o comando para adicionar outros professores. Proteja o
   arquivo e faça uma cópia segura: perdê-lo invalida as contas configuradas.

3. Na raiz do repositório, execute a aplicação:

   ```
   uvicorn src.app:app --host 127.0.0.1 --port 8000
   ```

4. Abra seu navegador e vá para:
   - Aplicação: http://localhost:8000/
   - Documentação da API: http://localhost:8000/docs
   - Documentação alternativa: http://localhost:8000/redoc

## Endpoints da API

| Método | Endpoint                                                          | Descrição                                                           |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Obter todas as atividades com seus detalhes e contagem atual de participantes |
| POST   | `/auth/login` | Autenticar professor com JSON `username` e `password` |
| GET    | `/auth/session` | Consultar a sessão atual |
| POST   | `/auth/logout` | Encerrar a sessão de professor |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Inscrever estudante (requer login) |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Remover inscrição (requer login) |

O login cria um cookie de sessão com duração de até oito horas. As sessões ficam
na memória e são perdidas ao reiniciar o servidor; execute uma única instância
da aplicação. Em produção, use HTTPS e configure corretamente o proxy reverso
para que a aplicação reconheça o esquema HTTPS. O cookie é marcado como seguro
quando a requisição é HTTPS. A aplicação não implementa limitação de tentativas
de login; configure-a no proxy antes de expor o serviço publicamente.

## Modelo de Dados

A aplicação usa um modelo de dados simples com identificadores significativos:

1. **Atividades** - Usa o nome da atividade como identificador:

   - Descrição
   - Cronograma
   - Número máximo de participantes permitidos
   - Lista de emails de estudantes que estão inscritos

2. **Estudantes** - Usa o email como identificador.

Atividades e inscrições são armazenadas em memória e serão reiniciadas quando o
servidor reiniciar. Apenas as credenciais de professores persistem no arquivo local.
