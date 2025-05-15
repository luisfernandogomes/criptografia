from flask import Flask, jsonify,request
from sqlalchemy import select
from models import UsuarioExemplo, NotasExemplo, SessionLocalExemplo
from flask_jwt_extended import get_jwt_identity, JWTManager, create_access_token
from functools import wraps
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'senha'
jwt = JWTManager(app)

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        db_session = SessionLocalExemplo()
        try:
            user = db_session.execute(select(UsuarioExemplo).where(UsuarioExemplo.id == current_user)).scalar()
            if user and user.papel == 'admin':
                return fn(*args, **kwargs)

            return jsonify({'error':'usuario não possui permissão de administrador'})
        finally:
            db_session.close()
    return wrapper

@app.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    email = dados['email']
    senha = dados['senha']
    db_session = SessionLocalExemplo()
    try:
        user = db_session.execute(select(UsuarioExemplo).where(UsuarioExemplo.email == email)).scalar()
        if user and user.check_password(senha):
            access_token = create_access_token(identity=email)
            return jsonify(access_token=access_token)
        return jsonify({ 'error': 'Senha incorreto' })
    finally:
        db_session.close()

@app.route('/cadastro', methods=['POST'])
def cadastro():
    dados = request.get_json()
    nome = dados['nome']
    email = dados['email']
    papel = dados.get('papel', 'usuario')
    senha = dados['senha']

    if not nome or not email or not senha:
        return jsonify({"msg": "Nome de usuário e senha são obrigatórios"}), 400

    banco = SessionLocalExemplo()
    try:
        # Verificar se o usuário já existe
        user_check = select(UsuarioExemplo).where(UsuarioExemplo.email == email)
        usuario_existente = banco.execute(user_check).scalar()

        if usuario_existente:
            return jsonify({"msg": "Usuário já existe"}), 400

        novo_usuario = UsuarioExemplo(nome=nome, email=email, papel=papel)
        novo_usuario.set_senha_hash(senha)
        banco.add(novo_usuario)
        banco.commit()

        user_id = novo_usuario.id
        return jsonify({"msg": "Usuário criado com sucesso", "user_id": user_id}), 201
    except Exception as e:
        banco.rollback()
        return jsonify({"msg": f"Erro ao registrar usuário: {str(e)}"}), 500
    finally:
        banco.close()

@app.route('/notas_exemplo', methods=['POST'])
def criar_nota_exemplo():
    data = request.get_json()
    conteudo = data.get('conteudo')

    if not conteudo:
        return jsonify({"msg": "Conteúdo da nota é obrigatório"}), 400

    db = SessionLocalExemplo()
    try:
        nova_nota = NotasExemplo(conteudo=conteudo)
        # Se quisesse associar ao usuário: nova_nota.user_id = current_user_id
        db.add(nova_nota)
        db.commit()
        nota_id = nova_nota.id
        return jsonify({"msg": "Nota criada", "nota_id": nota_id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"msg": f"Erro ao criar nota: {str(e)}"}), 500
    finally:
        db.close()

@app.route('/notas_exemplo', methods=['GET'])
def listar_notas_exemplo():
    db = SessionLocalExemplo()
    try:
        stmt = select(NotasExemplo)
        notas_result = db.execute(stmt).scalars().all() # .scalars().all() para obter uma lista de objetos
        notas_list = [{"id": nota.id, "conteudo": nota.conteudo} for nota in notas_result]
        return jsonify(notas_list)
    finally:
        db.close()

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Rodar em uma porta diferente da API principal