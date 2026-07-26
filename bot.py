import asyncio
import json
import os
import random
import re
import secrets
import shlex
import sqlite3
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.interactions import InteractionResponse

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for environments without python-dotenv
    def load_dotenv() -> bool:
        return False

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = "bot_data.sqlite3"
COLOR = 0x50408F
DEFAULT_PREFIX = "*"
BLACK_FLASH_CHANCE_INICIAL = 20  # 1 chance em 20.
BLACK_FLASH_CHANCE_MAXIMA = 18  # Após acertos, o menor denominador é 18.
BLACK_FLASH_RESETA_EM_HORAS = 24
# ID numérico do usuário que sempre acerta. Este valor não é anunciado pelo bot.
BLACK_FLASH_USUARIO_GARANTIDO_ID = 1167687868899147786
VIOLETTE_ID = 1167687868899147786
CHELSEA_ID = [
    1512614083348926527,
    720491821507018762,
]
BLACK_FLASH_IMAGES = [
    "https://i.ibb.co/gZS4w35R/Viva-Cut-video-1784922097011-ezgif-com-video-to-gif-converter.gif",
    "https://i.ibb.co/dTZ3Mtf/ezgif-com-video-to-gif-converter.gif",
    "https://i.ibb.co/Tj73BPP/ezgif-com-video-to-gif-converter-3.gif",
    "https://i.ibb.co/MyWtSxWr/ezgif-com-video-to-gif-converter-4.gif",
]
VIOLENCE_GIF = "https://i.ibb.co/JWkhTZhK/ezgif-com-video-to-gif-converter-5.gif"
IMAGEM_ESPECIAL = "https://i.ibb.co/BHn9kMQW/074f2fdc35f01d4bc3c0565f9c83ea24-3316428614160596671-ezgif-com-resize.gif"
IMAGEM_NORMAL = "https://i.ibb.co/nNKNnHs9/undefined-Imgur-ezgif-com-resize.gif"
CURSED_ENERGY_LEVELS = [
    {
        "nome": "Energia Amaldiçoada Baixa",
        "chance": 70,
        "imagem": "https://i.ibb.co/27QhzQRp/965ecb70c91beccff6acddd7c9c37433.gif",
        "descricao": "Pouca energia amaldiçoada."
    },

    {
        "nome": "Energia Amaldiçoada Moderada",
        "chance": 18,
        "imagem": "https://i.ibb.co/GQCbJSZW/867fca83c5b2f3a0da01e22a16be4971.gif",
        "descricao": "Um nível equilibrado de energia."
    },

    {
        "nome": "Energia Amaldiçoada Alta",
        "chance": 5,
        "imagem": "https://i.ibb.co/nNg8zq2M/94e4bfba3db7617ba7a754f0cf64b193.gif",
        "descricao": "Grandes reservas de energia amaldiçoada."
    },

    {
        "nome": "Sem Energia Amaldiçoada",
        "chance": 3,
        "imagem": "https://i.ibb.co/nMvJMXk3/8905af5c62a3ea0c3ed8d8d61962fe1e.gif",
        "descricao": "Quantidade inexistente de energia amaldiçoada."
    },

    {
        "nome": "Energia Amaldiçoada Massiva",
        "chance": 2.8,
        "imagem": "https://i.ibb.co/BV930KHG/0becc1f20de8909c7daa826c1221af67.gif",
        "descricao": "Uma quantidade extremamente rara."
    },

    {
        "nome": "Energia Amaldiçoada Irrestrita",
        "chance": 1,
        "imagem": "https://i.ibb.co/gFtb59CY/ezgif-com-resize.gif",
        "descricao": "Uma energia amaldiçoada colossal proveniente de uma Restrição Celestial. Sua quantidade é anormal, mas está ligada a uma condição de sacrifício."
    },

    {
        "nome": "Energia Amaldiçoada Transcendente",
        "chance": 0.2,
        "imagem": "https://i.ibb.co/bM6QSPWd/82900bf8197817eb9b94f18579ae402d.gif",
        "descricao": "Uma existência fora da escala conhecida."
    }
]


def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (guild_id INTEGER PRIMARY KEY, prefix TEXT NOT NULL DEFAULT '*');
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, code TEXT NOT NULL,
                name TEXT NOT NULL, category TEXT NOT NULL, slots INTEGER NOT NULL, UNIQUE(guild_id, code));
            CREATE TABLE IF NOT EXISTS vacancy_members (vacancy_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                PRIMARY KEY(vacancy_id, user_id));
            CREATE TABLE IF NOT EXISTS profiles (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, points INTEGER NOT NULL DEFAULT 0,
                strength INTEGER NOT NULL DEFAULT 0, defense INTEGER NOT NULL DEFAULT 0, energy INTEGER NOT NULL DEFAULT 0,
                cursed_energy TEXT DEFAULT NULL, balance INTEGER NOT NULL DEFAULT 0, rolls INTEGER NOT NULL DEFAULT 5,
                last_checkin TEXT, PRIMARY KEY(guild_id, user_id));
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, code TEXT NOT NULL,
                name TEXT NOT NULL, description TEXT NOT NULL, UNIQUE(guild_id, code));
            CREATE TABLE IF NOT EXISTS inventory (guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(guild_id, user_id, item_id));
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
                message_id INTEGER, prize TEXT NOT NULL, winners INTEGER NOT NULL, ends_at TEXT NOT NULL, ended INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS giveaway_entries (giveaway_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                PRIMARY KEY(giveaway_id, user_id));
            CREATE TABLE IF NOT EXISTS vacancy_backups (
                code TEXT PRIMARY KEY, source_guild_id INTEGER NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS black_flash_stats (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, chance INTEGER NOT NULL DEFAULT 20,
                last_used TEXT, PRIMARY KEY(guild_id, user_id));
        """)

        for statement in (
            "ALTER TABLE profiles ADD COLUMN cursed_energy TEXT DEFAULT NULL",
            "ALTER TABLE profiles ADD COLUMN rolls INTEGER NOT NULL DEFAULT 5",
        ):
            try:
                conn.execute(statement)
            except sqlite3.OperationalError:
                pass


def profile(guild_id: int, user_id: int):
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO profiles (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
        return conn.execute("SELECT * FROM profiles WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()


def ensure_profile(guild_id: int, user_id: int) -> None:
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO profiles (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))


def set_profile_text(guild_id: int, user_id: int, field: str, value: str | None) -> None:
    ensure_profile(guild_id, user_id)
    with db() as conn:
        conn.execute(f"UPDATE profiles SET {field}=? WHERE guild_id=? AND user_id=?", (value, guild_id, user_id))


def adjust_profile_int(guild_id: int, user_id: int, field: str, delta: int) -> None:
    ensure_profile(guild_id, user_id)
    with db() as conn:
        conn.execute(f"UPDATE profiles SET {field}=MAX(0, {field}+?) WHERE guild_id=? AND user_id=?", (delta, guild_id, user_id))


_original_send_message = InteractionResponse.send_message
_original_edit_message = InteractionResponse.edit_message


def _response_is_done(response) -> bool:
    try:
        done = getattr(response, "is_done", None)
        if callable(done):
            return bool(done())
        return bool(getattr(response, "_responded", False))
    except Exception:
        return False


async def _guarded_send_message(self, *args, **kwargs):
    if _response_is_done(self):
        return None
    try:
        return await _original_send_message(self, *args, **kwargs)
    except discord.NotFound:
        return None
    except Exception as exc:
        if "respond" in str(exc).lower() or "already" in str(exc).lower():
            return None
        raise


async def _guarded_edit_message(self, *args, **kwargs):
    if _response_is_done(self):
        return None
    try:
        return await _original_edit_message(self, *args, **kwargs)
    except discord.NotFound:
        return None
    except Exception as exc:
        if "respond" in str(exc).lower() or "already" in str(exc).lower():
            return None
        raise


InteractionResponse.send_message = _guarded_send_message
InteractionResponse.edit_message = _guarded_edit_message


def is_admin(interaction: discord.Interaction) -> bool:
    return isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator


async def respond(interaction: discord.Interaction, *args, **kwargs):
    if _response_is_done(interaction.response):
        try:
            return await interaction.followup.send(*args, **kwargs)
        except Exception:
            return None
    try:
        return await interaction.response.send_message(*args, **kwargs)
    except discord.NotFound:
        return None
    except Exception as exc:
        if "respond" in str(exc).lower() or "already" in str(exc).lower():
            try:
                return await interaction.followup.send(*args, **kwargs)
            except Exception:
                return None
        raise


async def edit_reply(interaction: discord.Interaction, *args, **kwargs):
    try:
        return await interaction.response.edit_message(*args, **kwargs)
    except discord.NotFound:
        return None
    except Exception as exc:
        if "respond" in str(exc).lower() or "already" in str(exc).lower():
            return None
        raise


async def admin_only(interaction: discord.Interaction) -> bool:
    return is_admin(interaction)


def guild_required(interaction: discord.Interaction) -> bool:
    return interaction.guild is not None


def format_vacancy(row: sqlite3.Row) -> str:
    occupants = ", ".join(f"<@{user_id}>" for user_id in (row["occupants"] or "").split(",") if user_id)
    people = occupants or "Disponível"
    return f"**{row['code']}** — {row['name']} ({row['category']}) · `{row['occupied']}/{row['slots']}`\n└ {people}"


def create_vacancy_backup(guild_id: int) -> tuple[str, int]:
    """Salva apenas a estrutura das vagas e devolve código e quantidade."""
    with db() as conn:
        rows = conn.execute("SELECT code, name, category, slots FROM vacancies WHERE guild_id=? ORDER BY id", (guild_id,)).fetchall()
        if not rows:
            return "", 0
        data = json.dumps([dict(row) for row in rows], ensure_ascii=False)
        for _ in range(10):
            code = f"VAGAS-{secrets.token_hex(4).upper()}"
            try:
                conn.execute("INSERT INTO vacancy_backups (code, source_guild_id, data, created_at) VALUES (?, ?, ?, ?)", (code, guild_id, data, datetime.now(timezone.utc).isoformat()))
                return code, len(rows)
            except sqlite3.IntegrityError:
                continue
    raise RuntimeError("Não foi possível criar um código de backup único.")


def restore_vacancy_backup(guild_id: int, code: str) -> tuple[int, int] | None:
    """Importa vagas ausentes; códigos já existentes são preservados."""
    with db() as conn:
        backup = conn.execute("SELECT data FROM vacancy_backups WHERE code=?", (code.upper(),)).fetchone()
        if not backup:
            return None
        try:
            vacancies = json.loads(backup["data"])
        except json.JSONDecodeError:
            raise RuntimeError("O backup está corrompido.")
        imported = skipped = 0
        for vacancy in vacancies:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO vacancies (guild_id, code, name, category, slots) VALUES (?, ?, ?, ?, ?)",
                (guild_id, vacancy["code"], vacancy["name"], vacancy["category"], vacancy["slots"]),
            )
            if cursor.rowcount:
                imported += 1
            else:
                skipped += 1
    return imported, skipped


def attempt_black_flash(guild_id: int, user_id: int) -> bool:
    """Tenta um Black Flash e registra a progressão de chance do usuário."""
    now = datetime.now(timezone.utc)
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO black_flash_stats (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
        stats = conn.execute("SELECT chance, last_used FROM black_flash_stats WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()
        chance = stats["chance"]
        if stats["last_used"]:
            last_used = datetime.fromisoformat(stats["last_used"])
            if now - last_used >= timedelta(hours=BLACK_FLASH_RESETA_EM_HORAS):
                chance = BLACK_FLASH_CHANCE_INICIAL
        success = user_id == BLACK_FLASH_USUARIO_GARANTIDO_ID or random.randint(1, chance) == 1
        next_chance = max(BLACK_FLASH_CHANCE_MAXIMA, chance - 1) if success else chance
        conn.execute("UPDATE black_flash_stats SET chance=?, last_used=? WHERE guild_id=? AND user_id=?", (next_chance, now.isoformat(), guild_id, user_id))
    return success


def black_flash_embed(attacker: discord.abc.User, target: discord.abc.User, success: bool) -> discord.Embed:
    if success:
        description = f"💥 {attacker.mention} distorce o espaço e acerta um **BLACK FLASH** devastador em {target.mention}!"
        title, color = "⚫ BLACK FLASH", COLOR
    else:
        description = f"{attacker.mention} tenta concentrar a energia amaldiçoada contra {target.mention}, mas o **Black Flash** não acontece."
        title, color = "✦ Tentativa de Black Flash", COLOR
    embed = discord.Embed(title=title, description=description, color=color)
    if success:
        embed.set_image(url=random.choice(BLACK_FLASH_IMAGES))
    return embed

def violence_embed(attacker: discord.abc.User, target: discord.abc.User) -> discord.Embed:
    embed = discord.Embed(
        description=f"**{attacker.mention} começa a usar {target.mention} como uma bolinha de pingpong!**",
        color=COLOR,
    )

    embed.set_image(url=VIOLENCE_GIF)
    return embed

def roll_cursed_energy(user_id):
    if user_id == VIOLETTE_ID:
        return {
            "nome": "Energia Amaldiçoada Transcendente",
            "imagem": "https://i.ibb.co/bM6QSPWd/82900bf8197817eb9b94f18579ae402d.gif",
            "descricao": "Uma anomalia absoluta. Sua energia amaldiçoada ultrapassa todos os limites conhecidos."
        }

    valor = random.randint(1, 100)
    acumulado = 0

    for energia in CURSED_ENERGY_LEVELS:
        acumulado += energia["chance"]
        if valor <= acumulado:
            return energia

    # Fallback in case probabilities don't sum to cover the range
    return CURSED_ENERGY_LEVELS[-1] if CURSED_ENERGY_LEVELS else None

def criar_roll(guild_id: int, user_id: int):
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO profiles (guild_id, user_id) VALUES (?, ?)",
            (guild_id, user_id)
        )

        perfil = conn.execute(
            "SELECT rolls FROM profiles WHERE guild_id=? AND user_id= ?",
            (guild_id, user_id)
        ).fetchone()

        if perfil["rolls"] <= 0:
            return None

        resultado = roll_cursed_energy(user_id)
        if resultado is None:
            return None

        conn.execute(
            """
            UPDATE profiles
            SET rolls = rolls - 1,
                cursed_energy = ?
            WHERE guild_id=? AND user_id=?
            """,
            (
                resultado["nome"],
                guild_id,
                user_id
            )
        )

    return resultado

def quantidade_rolls(guild_id: int, user_id: int):
    p = profile(guild_id, user_id)
    return p["rolls"]

def help_embed(section: str = "início") -> discord.Embed:
    content = {
        "início": (
            "MENU PRINCIPAL",
            """
✦ **Sistema do bot**

Use tanto os prefixos (`*`) quanto os comandos de barra (`/`).

Funções principais:
- Perfil e status
- Energia Amaldiçoada
- Combate
- Economia
- Inventário
- Vagas
- Sorteios

Categorias:

⚔️ RPG
- Status
- Energia
- Rolls
- Investir pontos

💰 Economia
- Saldo
- Check-in
- Transferências
- Ranking

🎒 Recursos
- Inventário
- Itens

📋 Gerenciamento
- Vagas
- Backups de vagas

🎲 Diversão
- Dados
- Cara ou coroa
- Sorteios

⚙ Administração
- Prefixo
- Rolls
- Energia
- Itens
- Vagas
"""
        ),

        "rpg": (
            "SISTEMA RPG",
            """
Comandos de RPG:

`/status` ou `*status`
Mostra atributos, energia e saldo.

`/energia` ou `*energia`
Gera uma nova Energia Amaldiçoada.

`/rolls` ou `*rolls`
Mostra quantos rolls você possui.

`/status_investir` ou `*investir atributo`
Investe pontos livres em atributos.

Exemplos:
`/status_investir atributo:strength`
"""
        ),

        "combate": (
            "COMBATE",
            """
Comandos de combate:

`/soco_azul @membro`
Realiza um ataque usando energia amaldiçoada.

`/sequencia_golpes @membro`
Executa uma sequência de golpes.

`/black_flash @membro`
Tenta realizar um Black Flash.

`/violence @membro`
Comando especial reservado.
"""
        ),

        "economia": (
            "ECONOMIA",
            """
Sistema de moedas.

Comandos:

`/checkin`
Recebe recompensa diária.

`/saldo`
Mostra seu dinheiro.

`/transferir membro quantidade`
Transfere moedas para outro usuário.

`/ranking`
Mostra os maiores saldos.
"""
        ),

        "inventário": (
            "INVENTÁRIO",
            """
Sistema de itens.

Comandos:

`/inventario`
Mostra seus itens.

`/item código`
Consulta informações de um item.

`/inventario_adicionar` (admin)
Adiciona ou remove itens de um membro.
"""
        ),

        "vagas": (
            "SISTEMA DE VAGAS",
            """
Gerenciamento de grupos e posições.

Comandos:

`/vaga_criar` (admin)
Cria uma vaga.

`/vagas`
Lista vagas disponíveis.

`/vaga_entrar`
Entra em uma vaga.

`/vaga_sair`
Sai de uma vaga.

`/vaga_info`
Mostra suas vagas.

`/vagas_backup` e `/vagas_restaurar` (admin)
Criam e restauram backups de vagas.
"""
        ),

        "dados": (
            "DADOS",
            """
Sistema de rolagem para RPG.

Comando:

`/rolar expressao`

Exemplos:
`2d6`
`1d20+5`
`3d8-2`
"""
        ),

        "sorteios": (
            "SORTEIOS",
            """
Sistema de sorteios.

Comandos:

`/sorteio_iniciar` (admin)
Cria um sorteio.

`/sorteio_listar`
Lista sorteios ativos.

`/sorteio_encerrar` (admin)
Finaliza um sorteio.

`/sorteio_rerolar` (admin)
Escolhe novos vencedores.
"""
        ),

        "administração": (
            "ADMINISTRAÇÃO",
            """
Comandos administrativos:

`/configurar_prefixo`
Altera o prefixo do servidor.

`/dizer`
Envia mensagens pelo bot.

`/dizer_no_canal`
Envia mensagens em canais específicos.

`/dar_rolls` e `/remover_rolls`
Concedem ou removem rolls de um membro.

`/dar_energia` e `/remover_energia`
Definem ou removem a energia amaldiçoada de um membro.

`/item_criar`, `/status_pontos` e `/inventario_adicionar`
Gerenciam itens, pontos e inventário.
"""
        ),

        "utilidades": (
            "UTILIDADES",
            """
Comandos gerais:

`/ajuda` ou `*ajuda`
Abre este menu.

`/olar` ou `*olar`
Teste do bot.

`/cara_ou_coroa`
Joga cara ou coroa.

Prefixo padrão:
`*`
"""
        ),
    }

    title, description = content.get(
        section,
        content["início"]
    )

    embed = discord.Embed(
        title=f"✦ {title}",
        description=description,
        color=COLOR
    )

    embed.set_footer(
        text="Sistema RPG • Energia Amaldiçoada • Economia"
    )

    return embed


class HelpView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        choices = [
            discord.SelectOption(
                label="RPG",
                value="rpg"
            ),

            discord.SelectOption(
                label="Combate",
                value="combate"
            ),

            discord.SelectOption(
                label="Economia",
                value="economia"
            ),

            discord.SelectOption(
                label="Inventário",
                value="inventário"
            ),

            discord.SelectOption(
                label="Vagas",
                value="vagas"
            ),

            discord.SelectOption(
                label="Dados",
                value="dados"
            ),

            discord.SelectOption(
                label="Sorteios",
                value="sorteios"
            ),

            discord.SelectOption(
                label="Administração",
                value="administração"
            ),

            discord.SelectOption(
                label="Utilidades",
                value="utilidades"
            ),
        ]
        select = discord.ui.Select(placeholder="Selecione uma seção...", options=choices)
        select.callback = self.select_callback
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Este menu de ajuda pertence a outra pessoa. Use seu próprio comando de ajuda.")
            return False
        return True

    async def select_callback(self, interaction: discord.Interaction):
        section = interaction.data["values"][0]
        await interaction.response.edit_message(embed=help_embed(section), view=self)


class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        button = discord.ui.Button(label="Participar", emoji="🎉", style=discord.ButtonStyle.primary, custom_id=f"giveaway:{giveaway_id}")
        button.callback = self.join
        self.add_item(button)

    async def join(self, interaction: discord.Interaction):
        with db() as conn:
            draw = conn.execute("SELECT ended FROM giveaways WHERE id=?", (self.giveaway_id,)).fetchone()
            if not draw or draw["ended"]:
                await interaction.response.send_message("Este sorteio já terminou.")
                return
            conn.execute("INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)", (self.giveaway_id, interaction.user.id))
            count = conn.execute("SELECT COUNT(*) FROM giveaway_entries WHERE giveaway_id=?", (self.giveaway_id,)).fetchone()[0]
        await interaction.response.send_message(f"Participação confirmada! ({count} participante(s))")


class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.giveaway_tasks: dict[int, asyncio.Task] = {}

    async def setup_hook(self):
        initialize_database()
        with db() as conn:
            active = conn.execute("SELECT id, ends_at FROM giveaways WHERE ended=0").fetchall()
        for giveaway in active:
            self.add_view(GiveawayView(giveaway["id"]))
            self.schedule_giveaway(giveaway["id"], giveaway["ends_at"])
        await self.tree.sync()

    def schedule_giveaway(self, giveaway_id: int, ends_at: str):
        if giveaway_id not in self.giveaway_tasks:
            self.giveaway_tasks[giveaway_id] = asyncio.create_task(self.wait_and_finish(giveaway_id, ends_at))

    async def wait_and_finish(self, giveaway_id: int, ends_at: str):
        seconds = max(0, (datetime.fromisoformat(ends_at) - datetime.now(timezone.utc)).total_seconds())
        await asyncio.sleep(seconds)
        await finish_giveaway(giveaway_id, self)

    async def on_ready(self):
        print(f"Logado como {self.user} (ID: {self.user.id})")

    async def on_message(self, message: discord.Message):
        """Comandos tradicionais, por exemplo: *ajuda e *rolar 2d6+3."""
        if message.author.bot or not message.guild:
            return

        if any(user.id == VIOLETTE_ID for user in message.mentions):

            if message.author.id in CHELSEA_ID:
                descricao = (
    f"**{message.author.mention} chamou por ela...**\n\n"
    "Afinal, o que seria da Lua sem a Terra?"
)
                imagem = IMAGEM_ESPECIAL

            else:
                descricao = f"**{message.author.mention} ousou mencionar a Deusa da Lua.**"
                imagem = IMAGEM_NORMAL

            embed = discord.Embed(
                title="✦ A Maior Anomalia de Teyvat",
                description=descricao,
                color=COLOR
            )

            embed.set_image(url=imagem)

            await message.channel.send(embed=embed)


        with db() as conn:
            row = conn.execute("SELECT prefix FROM settings WHERE guild_id=?", (message.guild.id,)).fetchone()
        prefix = row["prefix"] if row else DEFAULT_PREFIX
        if not message.content.startswith(prefix):
            return
        try:
            parts = shlex.split(message.content[len(prefix):])
        except ValueError:
            await message.channel.send("Não consegui ler esse comando: confira as aspas.")
            return
        if not parts:
            return
        command, args = parts[0].lower(), parts[1:]
        admin = message.author.guild_permissions.administrator

        if command in ("ajuda", "help", "comandos"):
            await message.channel.send(embed=help_embed(), view=HelpView(message.author.id))
        elif command in ("prefix", "configurar_prefixo"):
            await message.channel.send(f"Prefixo atual: `{prefix}`. Para mudar: `{prefix}setprefix novo_prefixo`.")
        elif command == "setprefix":
            if not admin:
                await message.channel.send("Você precisa ser administrador para alterar o prefixo.")
            elif not args or len(args[0]) > 5:
                await message.channel.send(f"Uso: `{prefix}setprefix novo_prefixo` (máximo de 5 caracteres).")
            else:
                with db() as conn:
                    conn.execute("INSERT INTO settings (guild_id,prefix) VALUES (?,?) ON CONFLICT(guild_id) DO UPDATE SET prefix=excluded.prefix", (message.guild.id, args[0]))
                await message.channel.send(f"Prefixo alterado para `{args[0]}`.")
        elif command in ("rolar", "roll"):
            if not args:
                await message.channel.send(f"Uso: `{prefix}rolar 2d6+3`.")
                return
            match = re.fullmatch(r"(\d{1,3})d(\d{1,5})([+-]\d{1,5})?", args[0].lower())
            if not match:
                await message.channel.send("Formato inválido. Use `2d6+3`.")
                return
            count, sides, modifier = int(match[1]), int(match[2]), int(match[3] or 0)
            if count * sides > 1_000_000:
                await message.channel.send("Rolagem muito grande.")
                return
            rolls = [random.randint(1, sides) for _ in range(count)]
            shown = ", ".join(map(str, rolls)) if count <= 30 else f"{count} resultados"
            await message.channel.send(f"🎲 **{args[0]}** → [{shown}] {modifier:+d}\n**Total: {sum(rolls) + modifier}**")
        elif command in ("caraoucoroa", "cara_ou_coroa", "coinflip"):
            await message.channel.send(f"🪙 {message.author.mention}: **{random.choice(['Cara', 'Coroa'])}**!")
        elif command in ("vagas", "listar"):
            category = args[0] if args else None
            query, values = "SELECT v.*, COUNT(m.user_id) AS occupied, GROUP_CONCAT(m.user_id) AS occupants FROM vacancies v LEFT JOIN vacancy_members m ON v.id=m.vacancy_id WHERE v.guild_id=?", [message.guild.id]
            if category:
                query += " AND lower(v.category)=lower(?)"; values.append(category)
            query += " GROUP BY v.id ORDER BY v.category, v.code"
            with db() as conn:
                rows = conn.execute(query, values).fetchall()
            text = "\n".join(format_vacancy(r) for r in rows) or "Nenhuma vaga encontrada."
            await message.channel.send(embed=discord.Embed(title="📋 Lista de vagas", description=text[:4096], color=COLOR))
        elif command == "entrar":
            if not args:
                await message.channel.send(f"Uso: `{prefix}entrar CODIGO`."); return
            with db() as conn:
                vacancy = conn.execute("SELECT * FROM vacancies WHERE guild_id=? AND code=?", (message.guild.id, args[0].upper())).fetchone()
                if not vacancy:
                    await message.channel.send("Vaga não encontrada."); return
                occupied = conn.execute("SELECT COUNT(*) FROM vacancy_members WHERE vacancy_id=?", (vacancy["id"],)).fetchone()[0]
                if occupied >= vacancy["slots"]:
                    await message.channel.send("Essa vaga já está cheia."); return
                try: conn.execute("INSERT INTO vacancy_members VALUES (?, ?)", (vacancy["id"], message.author.id))
                except sqlite3.IntegrityError:
                    await message.channel.send("Você já está nessa vaga."); return
            await message.channel.send(f"{message.author.mention} entrou em **{vacancy['name']}**.")
        elif command == "sair":
            if not args:
                await message.channel.send(f"Uso: `{prefix}sair CODIGO`."); return
            with db() as conn:
                result = conn.execute("DELETE FROM vacancy_members WHERE user_id=? AND vacancy_id=(SELECT id FROM vacancies WHERE guild_id=? AND code=?)", (message.author.id, message.guild.id, args[0].upper()))
            await message.channel.send("Você saiu da vaga." if result.rowcount else "Você não faz parte dessa vaga.")
        elif command in ("status", "saldo"):
            member = message.mentions[0] if message.mentions else message.author
            p = profile(message.guild.id, member.id)
            if command == "saldo":
                await message.channel.send(f"💰 {member.mention} possui **{p['balance']}** moedas.")
            else:
                desc = (
                    f"Pontos livres: **{p['points']}**\n"
                    f"Força: **{p['strength']}** · Defesa: **{p['defense']}** · Energia: **{p['energy']}**\n"
                    f"Energia Amaldiçoada: **{p['cursed_energy'] or 'Não definida'}**\n"
                    f"Saldo: **{p['balance']} moedas**"
                )
                await message.channel.send(embed=discord.Embed(title=f"⚔️ Status de {member.display_name}", description=desc, color=COLOR))

        elif command == "rolls":
            rolls = quantidade_rolls(
                message.guild.id,
                message.author.id
            )

            await message.channel.send(
                f"🎲 {message.author.mention}, você possui **{rolls} rolls**."
            )
        elif command in ("inv", "inventario"):
            member = message.mentions[0] if message.mentions else message.author
            with db() as conn:
                rows = conn.execute("SELECT i.code, i.name, inv.quantity FROM inventory inv JOIN items i ON i.id=inv.item_id WHERE inv.guild_id=? AND inv.user_id=? AND inv.quantity>0", (message.guild.id, member.id)).fetchall()
            text = "\n".join(f"`{r['code']}` {r['name']} ×{r['quantity']}" for r in rows) or "Inventário vazio."
            await message.channel.send(embed=discord.Embed(title=f"🎒 Inventário de {member.display_name}", description=text, color=COLOR))
        elif command == "item":
            if not args:
                await message.channel.send(f"Uso: `{prefix}item CODIGO`."); return
            with db() as conn:
                row = conn.execute("SELECT * FROM items WHERE guild_id=? AND code=?", (message.guild.id, args[0].upper())).fetchone()
            await message.channel.send(embed=discord.Embed(title=f"{row['code']} — {row['name']}", description=row['description'], color=COLOR) if row else "Item não encontrado.")
        elif command == "checkin":
            p = profile(message.guild.id, message.author.id); now = datetime.now(timezone.utc)
            if p["last_checkin"] and datetime.fromisoformat(p["last_checkin"]).date() == now.date():
                await message.channel.send("Você já fez check-in hoje."); return
            with db() as conn:
                conn.execute("UPDATE profiles SET balance=balance+100, last_checkin=? WHERE guild_id=? AND user_id=?", (now.isoformat(), message.guild.id, message.author.id))
            await message.channel.send("✅ Check-in concluído: você recebeu **100 moedas**.")
        elif command == "ranking":
            with db() as conn:
                rows = conn.execute("SELECT user_id, balance FROM profiles WHERE guild_id=? ORDER BY balance DESC LIMIT 10", (message.guild.id,)).fetchall()
            text = "\n".join(f"{i}. <@{r['user_id']}> — **{r['balance']}**" for i, r in enumerate(rows, 1)) or "Ainda não há dados."
            await message.channel.send(embed=discord.Embed(title="🏆 Ranking", description=text, color=COLOR))
        elif command in ("criarvaga", "vaga_criar"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
            elif len(args) != 4 or not args[3].isdigit() or not 1 <= int(args[3]) <= 999:
                await message.channel.send(f"Uso: `{prefix}criarvaga CODIGO \"Nome\" \"Categoria\" quantidade`.")
            else:
                with db() as conn:
                    try:
                        conn.execute("INSERT INTO vacancies (guild_id, code, name, category, slots) VALUES (?, ?, ?, ?, ?)", (message.guild.id, args[0].upper(), args[1], args[2], int(args[3])))
                    except sqlite3.IntegrityError:
                        await message.channel.send("Já existe uma vaga com esse código."); return
                await message.channel.send(f"Vaga `{args[0].upper()}` criada com sucesso.")
        elif command in ("backupvagas", "vagas_backup"):
            if not admin:
                await message.channel.send("Você precisa ser administrador para criar um backup.")
            else:
                code, count = create_vacancy_backup(message.guild.id)
                if not code:
                    await message.channel.send("Não há vagas para salvar.")
                else:
                    await message.channel.send(f"✅ Backup de **{count}** vaga(s) criado. Código: `{code}`\nEm outro servidor, um administrador deve usar `{prefix}restaurarvagas {code}`.")
        elif command in ("restaurarvagas", "vagas_restaurar"):
            if not admin:
                await message.channel.send("Você precisa ser administrador para restaurar um backup.")
            elif not args:
                await message.channel.send(f"Uso: `{prefix}restaurarvagas VAGAS-CODIGO`.")
            else:
                result = restore_vacancy_backup(message.guild.id, args[0])
                if result is None:
                    await message.channel.send("Backup não encontrado.")
                else:
                    imported, skipped = result
                    await message.channel.send(f"✅ Backup restaurado: **{imported}** vaga(s) importada(s) e **{skipped}** ignorada(s) por já existir um código igual. Ocupantes não são copiados.")
        elif command in ("info", "vaga_info"):
            member = message.mentions[0] if message.mentions else message.author
            with db() as conn:
                rows = conn.execute("SELECT v.code, v.name FROM vacancies v JOIN vacancy_members m ON v.id=m.vacancy_id WHERE v.guild_id=? AND m.user_id=?", (message.guild.id, member.id)).fetchall()
            text = "\n".join(f"`{r['code']}` — {r['name']}" for r in rows) or "Nenhuma vaga ocupada."
            await message.channel.send(embed=discord.Embed(title=f"Vagas de {member.display_name}", description=text, color=COLOR))
        elif command in ("investir", "status_investir"):
            attributes = {"forca": "strength", "força": "strength", "defesa": "defense", "energia": "energy"}
            attribute = attributes.get(args[0].lower()) if args else None
            if not attribute:
                await message.channel.send(f"Uso: `{prefix}investir forca`, `{prefix}investir defesa` ou `{prefix}investir energia`.")
            else:
                p = profile(message.guild.id, message.author.id)
                if p["points"] < 1:
                    await message.channel.send("Você não tem pontos livres.")
                else:
                    with db() as conn:
                        conn.execute(f"UPDATE profiles SET points=points-1, {attribute}={attribute}+1 WHERE guild_id=? AND user_id=?", (message.guild.id, message.author.id))
                    await message.channel.send(f"1 ponto investido em **{args[0].title()}**.")
        elif command in ("darpontos", "status_pontos"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
            elif not message.mentions or len(args) < 2:
                await message.channel.send(f"Uso: `{prefix}darpontos @membro quantidade`.")
            else:
                try: amount = int(args[-1])
                except ValueError:
                    await message.channel.send("A quantidade precisa ser um número."); return
                if not -999 <= amount <= 999:
                    await message.channel.send("A quantidade deve estar entre -999 e 999."); return
                member = message.mentions[0]; profile(message.guild.id, member.id)
                with db() as conn:
                    conn.execute("UPDATE profiles SET points=MAX(0, points+?) WHERE guild_id=? AND user_id=?", (amount, message.guild.id, member.id))
                await message.channel.send("Pontos atualizados.")
        elif command in ("criaritem", "item_criar"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
            elif len(args) != 3:
                await message.channel.send(f"Uso: `{prefix}criaritem CODIGO \"Nome\" \"Descrição\"`.")
            else:
                with db() as conn:
                    try:
                        conn.execute("INSERT INTO items (guild_id, code, name, description) VALUES (?, ?, ?, ?)", (message.guild.id, args[0].upper(), args[1], args[2]))
                    except sqlite3.IntegrityError:
                        await message.channel.send("Esse código já existe."); return
                await message.channel.send("Item cadastrado.")
        elif command in ("adicionaritem", "inventario_adicionar"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
            elif not message.mentions or len(args) < 3:
                await message.channel.send(f"Uso: `{prefix}adicionaritem @membro CODIGO quantidade`.")
            else:
                try: amount = int(args[-1])
                except ValueError:
                    await message.channel.send("A quantidade precisa ser um número."); return
                if not -999 <= amount <= 999:
                    await message.channel.send("A quantidade deve estar entre -999 e 999."); return
                with db() as conn:
                    item_row = conn.execute("SELECT id FROM items WHERE guild_id=? AND code=?", (message.guild.id, args[-2].upper())).fetchone()
                    if not item_row:
                        await message.channel.send("Item não encontrado."); return
                    conn.execute("INSERT INTO inventory (guild_id,user_id,item_id,quantity) VALUES (?,?,?,MAX(0,?)) ON CONFLICT(guild_id,user_id,item_id) DO UPDATE SET quantity=MAX(0, quantity+excluded.quantity)", (message.guild.id, message.mentions[0].id, item_row["id"], amount))
                await message.channel.send("Inventário atualizado.")
        elif command == "transferir":
            if not message.mentions or len(args) < 2:
                await message.channel.send(f"Uso: `{prefix}transferir @membro quantidade`.")
            else:
                try: amount = int(args[-1])
                except ValueError:
                    await message.channel.send("A quantidade precisa ser um número."); return
                member = message.mentions[0]; p = profile(message.guild.id, message.author.id)
                if amount < 1 or member.bot or member.id == message.author.id:
                    await message.channel.send("Escolha outro membro e uma quantidade positiva.")
                elif p["balance"] < amount:
                    await message.channel.send("Saldo insuficiente.")
                else:
                    profile(message.guild.id, member.id)
                    with db() as conn:
                        conn.execute("UPDATE profiles SET balance=balance-? WHERE guild_id=? AND user_id=?", (amount, message.guild.id, message.author.id))
                        conn.execute("UPDATE profiles SET balance=balance+? WHERE guild_id=? AND user_id=?", (amount, message.guild.id, member.id))
                    await message.channel.send(f"Transferidas **{amount}** moedas para {member.mention}.")
        elif command in ("sorteio", "sorteio_iniciar"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
            elif len(args) not in (2, 3) or not args[-1].isdigit() or (len(args) == 3 and not args[-2].isdigit()):
                await message.channel.send(f"Uso: `{prefix}sorteio \"Prêmio\" minutos [vencedores]`.")
            else:
                prize = args[0]; minutes = int(args[1]); winners = int(args[2]) if len(args) == 3 else 1
                if not 1 <= minutes <= 10080 or not 1 <= winners <= 20:
                    await message.channel.send("Minutos: 1–10080. Vencedores: 1–20."); return
                ends_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
                with db() as conn:
                    cursor = conn.execute("INSERT INTO giveaways (guild_id, channel_id, prize, winners, ends_at) VALUES (?, ?, ?, ?, ?)", (message.guild.id, message.channel.id, prize, winners, ends_at.isoformat()))
                    giveaway_id = cursor.lastrowid
                view = GiveawayView(giveaway_id)
                giveaway_message = await message.channel.send(f"🎉 **SORTEIO: {prize}**\nTermina <t:{int(ends_at.timestamp())}:R> · {winners} vencedor(es).", view=view)
                with db() as conn:
                    conn.execute("UPDATE giveaways SET message_id=? WHERE id=?", (giveaway_message.id, giveaway_id))
                self.add_view(view); self.schedule_giveaway(giveaway_id, ends_at.isoformat())
        elif command in ("sorteios", "sorteio_listar"):
            with db() as conn:
                rows = conn.execute("SELECT * FROM giveaways WHERE guild_id=? AND ended=0 ORDER BY ends_at", (message.guild.id,)).fetchall()
            text = "\n".join(f"`#{r['id']}` {r['prize']} — termina <t:{int(datetime.fromisoformat(r['ends_at']).timestamp())}:R>" for r in rows) or "Nenhum sorteio ativo."
            await message.channel.send(embed=discord.Embed(title="🎉 Sorteios ativos", description=text, color=COLOR))
        elif command in ("encerrarsorteio", "sorteio_encerrar", "rerolarsorteio", "sorteio_rerolar"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
            elif not args or not args[0].isdigit():
                await message.channel.send(f"Uso: `{prefix}{command} ID_DO_SORTEIO`.")
            else:
                await finish_giveaway(int(args[0]), self, reroll=command in ("rerolarsorteio", "sorteio_rerolar"))
        elif command in ("dizercanal", "dizer_no_canal"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
            elif not message.channel_mentions or len(args) < 2:
                await message.channel.send(f"Uso: `{prefix}dizercanal #canal sua mensagem`.")
            else:
                await message.channel_mentions[0].send(" ".join(args[1:]))
                await message.channel.send("Mensagem enviada.")
        elif command in ("dizer", "say"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
            elif args:
                await message.channel.send(" ".join(args))
            else:
                await message.channel.send(f"Uso: `{prefix}dizer sua mensagem`.")
        elif command in ("olar", "ola"):
            await message.channel.send("Olá, mundo!")
        elif command in ("soco_azul", "bluepunch"):
            if not message.mentions:
                await message.channel.send(f"Uso: `{prefix}soco_azul @membro`.")
                return
            alvo = message.mentions[0]
            embed = discord.Embed(
                description=f"{message.author.mention} desfere um soco reforçado com energia amaldiçoada em azul contra {alvo.mention}!",
                color=COLOR,
            )
            embed.set_image(url="https://i.ibb.co/Zp2RSVny/ezgif-com-video-to-gif-converter-1.gif")
            await message.channel.send(embed=embed)
        elif command in ("sequencia_golpes", "hitsequence"):
            if not message.mentions:
                await message.channel.send(f"Uso: `{prefix}sequencia_golpes @membro`.")
                return
            alvo = message.mentions[0]
            embed = discord.Embed(
                description=f"{message.author.mention} desfere uma sequência de golpes contra {alvo.mention}!",
                color=COLOR,
            )
            embed.set_image(url="https://i.ibb.co/Hp21FQxD/ezgif-com-video-to-gif-converter-2.gif")
            await message.channel.send(embed=embed)
        elif command in ("energia", "energia_amaldicoada"):

            resultado = criar_roll(
                message.guild.id,
                message.author.id
            )

            if resultado is None:
                await message.channel.send(
                    "❌ Você não possui mais rolls disponíveis."
                )
                return

            embed = discord.Embed(
                title="✦ Resultado da Energia Amaldiçoada",
                color=COLOR
            )

            embed.add_field(
                name="Usuário",
                value=message.author.mention,
                inline=False
            )

            embed.add_field(
                name="Energia Obtida",
                value=f"⚫ {resultado['nome']}",
                inline=False
            )

            embed.add_field(
                name="Descrição",
                value=resultado["descricao"],
                inline=False
            )

            embed.set_image(
                url=resultado["imagem"]
            )

            await message.channel.send(embed=embed)

        elif command in ("blackflash", "black_flash"):
            if not message.mentions:
                await message.channel.send(f"Uso: `{prefix}blackflash @membro`.")
                return
            alvo = message.mentions[0]
            success = attempt_black_flash(message.guild.id, message.author.id)
            await message.channel.send(embed=black_flash_embed(message.author, alvo, success))

        elif command == "violence":
            if message.author.id != BLACK_FLASH_USUARIO_GARANTIDO_ID:
                await message.channel.send("❌ Você não pode usar esse comando.")
                return

            if not message.mentions:
                await message.channel.send(f"Uso: `{prefix}violence @membro`.")
                return

            alvo = message.mentions[0]

            if alvo.bot:
                await message.channel.send("Você não pode usar esse comando em bots.")
                return

            if alvo.id == message.author.id:
                await message.channel.send("Você não pode usar esse comando em si mesmo.")
                return

            await message.channel.send(
                embed=violence_embed(message.author, alvo)
            )

        elif command in ("darrolls", "dar_rolls"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
                return
            if not message.mentions or len(args) < 1:
                await message.channel.send(f"Uso: `{prefix}darrolls @membro quantidade`.")
                return
            try:
                amount = int(args[-1])
            except ValueError:
                await message.channel.send("A quantidade precisa ser um número.")
                return
            if not 1 <= amount <= 999:
                await message.channel.send("A quantidade deve estar entre 1 e 999.")
                return
            membro = message.mentions[0]
            adjust_profile_int(message.guild.id, membro.id, "rolls", amount)
            await message.channel.send(f"Adicionados **{amount}** rolls para {membro.mention}.")

        elif command in ("removerrolls", "remover_rolls"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
                return
            if not message.mentions or len(args) < 1:
                await message.channel.send(f"Uso: `{prefix}removerrolls @membro quantidade`.")
                return
            try:
                amount = int(args[-1])
            except ValueError:
                await message.channel.send("A quantidade precisa ser um número.")
                return
            if not 1 <= amount <= 999:
                await message.channel.send("A quantidade deve estar entre 1 e 999.")
                return
            membro = message.mentions[0]
            adjust_profile_int(message.guild.id, membro.id, "rolls", -amount)
            await message.channel.send(f"Removidos **{amount}** rolls de {membro.mention}.")

        elif command in ("darenergia", "dar_energia"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
                return
            if not message.mentions or len(args) < 2:
                await message.channel.send(f"Uso: `{prefix}darenergia @membro nome`.")
                return
            membro = message.mentions[0]
            energia = " ".join(args[1:])
            set_profile_text(message.guild.id, membro.id, "cursed_energy", energia)
            await message.channel.send(f"Energia de {membro.mention} alterada para **{energia}**.")

        elif command in ("removerenergia", "remover_energia"):
            if not admin:
                await message.channel.send("Você precisa ser administrador.")
                return
            if not message.mentions:
                await message.channel.send(f"Uso: `{prefix}removerenergia @membro`.")
                return
            membro = message.mentions[0]
            set_profile_text(message.guild.id, membro.id, "cursed_energy", None)
            await message.channel.send(f"Energia amaldiçoada removida de {membro.mention}.")

bot = MyClient()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    if isinstance(error, app_commands.CheckFailure):
        await respond(interaction, "Você precisa ser administrador para usar este comando.")
        return

    if isinstance(error, discord.NotFound):
        return

    await respond(interaction, "Ocorreu um erro ao executar este comando.")


async def finish_giveaway(giveaway_id: int, client: MyClient, reroll: bool = False):
    with db() as conn:
        giveaway = conn.execute("SELECT * FROM giveaways WHERE id=?", (giveaway_id,)).fetchone()
        if not giveaway or (giveaway["ended"] and not reroll): return
        entries = [row[0] for row in conn.execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id=?", (giveaway_id,))]
        winners = random.sample(entries, min(giveaway["winners"], len(entries))) if entries else []
        if not reroll: conn.execute("UPDATE giveaways SET ended=1 WHERE id=?", (giveaway_id,))
    channel = client.get_channel(giveaway["channel_id"])
    if channel:
        mentions = ", ".join(f"<@{user_id}>" for user_id in winners) or "ninguém (não houve participantes)"
        action = "Novo resultado" if reroll else "Sorteio encerrado"
        await channel.send(f"🎉 **{action}: {giveaway['prize']}**\nVencedor(es): {mentions}")


@bot.tree.command(name="ajuda", description="Abre o menu de ajuda")
async def ajuda(interaction: discord.Interaction):
    await respond(interaction, embed=help_embed(), view=HelpView(interaction.user.id))


@bot.tree.command(name="vaga_criar", description="[Admin] Cria uma vaga")
@app_commands.check(admin_only)
async def vaga_criar(interaction: discord.Interaction, codigo: str, nome: str, categoria: str, vagas: app_commands.Range[int, 1, 999]):
    with db() as conn:
        try: conn.execute("INSERT INTO vacancies (guild_id, code, name, category, slots) VALUES (?, ?, ?, ?, ?)", (interaction.guild_id, codigo.upper(), nome, categoria, vagas))
        except sqlite3.IntegrityError:
            await interaction.response.send_message("Já existe uma vaga com esse código."); return
    await interaction.response.send_message(f"Vaga `{codigo.upper()}` criada com sucesso.")


@bot.tree.command(name="vagas", description="Lista todas as vagas")
async def vagas(interaction: discord.Interaction, categoria: str | None = None):
    query, args = "SELECT v.*, COUNT(m.user_id) AS occupied, GROUP_CONCAT(m.user_id) AS occupants FROM vacancies v LEFT JOIN vacancy_members m ON v.id=m.vacancy_id WHERE v.guild_id=?", [interaction.guild_id]
    if categoria: query += " AND lower(v.category)=lower(?)"; args.append(categoria)
    query += " GROUP BY v.id ORDER BY v.category, v.code"
    with db() as conn: rows = conn.execute(query, args).fetchall()
    if not rows: await interaction.response.send_message("Nenhuma vaga encontrada."); return
    lines = [format_vacancy(r) for r in rows]
    await interaction.response.send_message(embed=discord.Embed(title="📋 Lista de vagas", description="\n".join(lines)[:4096], color=COLOR))


@bot.tree.command(name="vaga_entrar", description="Entra em uma vaga disponível")
async def vaga_entrar(interaction: discord.Interaction, codigo: str):
    with db() as conn:
        vacancy = conn.execute("SELECT * FROM vacancies WHERE guild_id=? AND code=?", (interaction.guild_id, codigo.upper())).fetchone()
        if not vacancy: await interaction.response.send_message("Vaga não encontrada."); return
        occupied = conn.execute("SELECT COUNT(*) FROM vacancy_members WHERE vacancy_id=?", (vacancy["id"],)).fetchone()[0]
        if occupied >= vacancy["slots"]: await interaction.response.send_message("Essa vaga já está cheia."); return
        try: conn.execute("INSERT INTO vacancy_members VALUES (?, ?)", (vacancy["id"], interaction.user.id))
        except sqlite3.IntegrityError: await interaction.response.send_message("Você já está nessa vaga."); return
    await interaction.response.send_message(f"Você entrou em **{vacancy['name']}**.")


@bot.tree.command(name="vaga_sair", description="Sai de uma vaga")
async def vaga_sair(interaction: discord.Interaction, codigo: str):
    with db() as conn:
        result = conn.execute("DELETE FROM vacancy_members WHERE user_id=? AND vacancy_id=(SELECT id FROM vacancies WHERE guild_id=? AND code=?)", (interaction.user.id, interaction.guild_id, codigo.upper()))
    await interaction.response.send_message("Você saiu da vaga." if result.rowcount else "Você não faz parte dessa vaga.")


@bot.tree.command(name="vaga_info", description="Mostra as vagas de um membro")
async def vaga_info(interaction: discord.Interaction, membro: discord.Member | None = None):
    member = membro or interaction.user
    with db() as conn: rows = conn.execute("SELECT v.code, v.name FROM vacancies v JOIN vacancy_members m ON v.id=m.vacancy_id WHERE v.guild_id=? AND m.user_id=?", (interaction.guild_id, member.id)).fetchall()
    text = "\n".join(f"`{r['code']}` — {r['name']}" for r in rows) or "Nenhuma vaga ocupada."
    await interaction.response.send_message(embed=discord.Embed(title=f"Vagas de {member.display_name}", description=text, color=COLOR))


@bot.tree.command(name="vagas_backup", description="[Admin] Cria um backup das vagas")
@app_commands.check(admin_only)
async def vagas_backup(interaction: discord.Interaction):
    code, count = create_vacancy_backup(interaction.guild_id)
    if not code:
        await interaction.response.send_message("Não há vagas para salvar.")
        return
    await interaction.response.send_message(f"Backup de **{count}** vaga(s) criado. Código: `{code}`\nUse `/vagas_restaurar` no outro servidor. Ocupantes não são copiados.")


@bot.tree.command(name="vagas_restaurar", description="[Admin] Restaura vagas de um código de backup")
@app_commands.check(admin_only)
async def vagas_restaurar(interaction: discord.Interaction, codigo: str):
    result = restore_vacancy_backup(interaction.guild_id, codigo)
    if result is None:
        await interaction.response.send_message("Backup não encontrado.")
        return
    imported, skipped = result
    await interaction.response.send_message(f"Backup restaurado: **{imported}** vaga(s) importada(s) e **{skipped}** ignorada(s) por terem código igual. Ocupantes não são copiados.")


@bot.tree.command(name="status", description="Mostra atributos e moedas")
async def status(interaction: discord.Interaction, membro: discord.Member | None = None):
    member = membro or interaction.user; p = profile(interaction.guild_id, member.id)
    await interaction.response.send_message(embed=discord.Embed(title=f"⚔️ Status de {member.display_name}", description=f"Pontos livres: **{p['points']}**\nForça: **{p['strength']}** · Defesa: **{p['defense']}** · Energia: **{p['energy']}**\nSaldo: **{p['balance']}** moedas", color=COLOR))


@bot.tree.command(name="status_investir", description="Investe um ponto em um atributo")
@app_commands.choices(atributo=[app_commands.Choice(name=x.title(), value=x) for x in ("strength", "defense", "energy")])
async def status_investir(interaction: discord.Interaction, atributo: app_commands.Choice[str]):
    p = profile(interaction.guild_id, interaction.user.id)
    if p["points"] < 1: await interaction.response.send_message("Você não tem pontos livres."); return
    with db() as conn: conn.execute(f"UPDATE profiles SET points=points-1, {atributo.value}={atributo.value}+1 WHERE guild_id=? AND user_id=?", (interaction.guild_id, interaction.user.id))
    await interaction.response.send_message(f"1 ponto investido em **{atributo.name}**.")


@bot.tree.command(name="status_pontos", description="[Admin] Dá pontos de atributo")
@app_commands.check(admin_only)
async def status_pontos(interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, -999, 999]):
    profile(interaction.guild_id, membro.id)
    with db() as conn: conn.execute("UPDATE profiles SET points=MAX(0, points+?) WHERE guild_id=? AND user_id=?", (quantidade, interaction.guild_id, membro.id))
    await interaction.response.send_message("Pontos atualizados.")


@bot.tree.command(name="dar_rolls", description="[Admin] Concede rolls a um membro")
@app_commands.check(admin_only)
async def dar_rolls(interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 999]):
    adjust_profile_int(interaction.guild_id, membro.id, "rolls", quantidade)
    await interaction.response.send_message(f"Adicionados **{quantidade}** rolls para {membro.mention}.")


@bot.tree.command(name="remover_rolls", description="[Admin] Remove rolls de um membro")
@app_commands.check(admin_only)
async def remover_rolls(interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 999]):
    adjust_profile_int(interaction.guild_id, membro.id, "rolls", -quantidade)
    await interaction.response.send_message(f"Removidos **{quantidade}** rolls de {membro.mention}.")


@bot.tree.command(name="dar_energia", description="[Admin] Define a energia amaldiçoada de um membro")
@app_commands.check(admin_only)
async def dar_energia(interaction: discord.Interaction, membro: discord.Member, energia: str):
    set_profile_text(interaction.guild_id, membro.id, "cursed_energy", energia)
    await interaction.response.send_message(f"Energia de {membro.mention} alterada para **{energia}**.")


@bot.tree.command(name="remover_energia", description="[Admin] Remove a energia amaldiçoada de um membro")
@app_commands.check(admin_only)
async def remover_energia(interaction: discord.Interaction, membro: discord.Member):
    set_profile_text(interaction.guild_id, membro.id, "cursed_energy", None)
    await interaction.response.send_message(f"Energia amaldiçoada removida de {membro.mention}.")


@bot.tree.command(name="item_criar", description="[Admin] Cadastra um item")
@app_commands.check(admin_only)
async def item_criar(interaction: discord.Interaction, codigo: str, nome: str, descricao: str):
    with db() as conn:
        try: conn.execute("INSERT INTO items (guild_id, code, name, description) VALUES (?, ?, ?, ?)", (interaction.guild_id, codigo.upper(), nome, descricao))
        except sqlite3.IntegrityError: await interaction.response.send_message("Esse código já existe."); return
    await interaction.response.send_message("Item cadastrado.")


@bot.tree.command(name="item", description="Consulta um item")
async def item(interaction: discord.Interaction, codigo: str):
    with db() as conn: row = conn.execute("SELECT * FROM items WHERE guild_id=? AND code=?", (interaction.guild_id, codigo.upper())).fetchone()
    if not row: await interaction.response.send_message("Item não encontrado."); return
    await interaction.response.send_message(embed=discord.Embed(title=f"{row['code']} — {row['name']}", description=row['description'], color=COLOR))


@bot.tree.command(name="inventario", description="Mostra o inventário")
async def inventario(interaction: discord.Interaction, membro: discord.Member | None = None):
    member = membro or interaction.user
    with db() as conn: rows = conn.execute("SELECT i.code, i.name, inv.quantity FROM inventory inv JOIN items i ON i.id=inv.item_id WHERE inv.guild_id=? AND inv.user_id=? AND inv.quantity>0", (interaction.guild_id, member.id)).fetchall()
    text = "\n".join(f"`{r['code']}` {r['name']} ×{r['quantity']}" for r in rows) or "Inventário vazio."
    await interaction.response.send_message(embed=discord.Embed(title=f"🎒 Inventário de {member.display_name}", description=text, color=COLOR))


@bot.tree.command(name="inventario_adicionar", description="[Admin] Adiciona ou remove itens")
@app_commands.check(admin_only)
async def inventario_adicionar(interaction: discord.Interaction, membro: discord.Member, codigo: str, quantidade: app_commands.Range[int, -999, 999]):
    with db() as conn:
        item_row = conn.execute("SELECT id FROM items WHERE guild_id=? AND code=?", (interaction.guild_id, codigo.upper())).fetchone()
        if not item_row: await interaction.response.send_message("Item não encontrado."); return
        conn.execute("INSERT INTO inventory (guild_id,user_id,item_id,quantity) VALUES (?,?,?,MAX(0,?)) ON CONFLICT(guild_id,user_id,item_id) DO UPDATE SET quantity=MAX(0, quantity+excluded.quantity)", (interaction.guild_id, membro.id, item_row["id"], quantidade))
    await interaction.response.send_message("Inventário atualizado.")


@bot.tree.command(name="rolar", description="Rola dados: 2d6+3, 1d20...")
async def rolar(interaction: discord.Interaction, expressao: str):
    match = re.fullmatch(r"(\d{1,3})d(\d{1,5})([+-]\d{1,5})?", expressao.lower().replace(" ", ""))
    if not match: await interaction.response.send_message("Formato inválido. Use, por exemplo, `2d6+3`."); return
    count, sides, modifier = int(match[1]), int(match[2]), int(match[3] or 0)
    if count * sides > 1_000_000: await interaction.response.send_message("Rolagem muito grande."); return
    rolls = [random.randint(1, sides) for _ in range(count)]; total = sum(rolls) + modifier
    shown = ", ".join(map(str, rolls)) if count <= 30 else f"{count} resultados"
    await interaction.response.send_message(f"🎲 **{expressao}** → [{shown}] {modifier:+d}\n**Total: {total}**")


@bot.tree.command(name="rolagem_ajuda", description="Mostra formatos de dados")
async def rolagem_ajuda(interaction: discord.Interaction):
    await interaction.response.send_message("Use `/rolar expressao:2d6+3`. Formatos aceitos: `XdY`, `XdY+N` e `XdY-N`.")


@bot.tree.command(name="cara_ou_coroa", description="Joga cara ou coroa")
async def cara_ou_coroa(interaction: discord.Interaction):
    await interaction.response.send_message(f"🪙 {interaction.user.mention}: **{random.choice(['Cara', 'Coroa'])}**!")


@bot.tree.command(name="checkin", description="Recebe as moedas diárias")
async def checkin(interaction: discord.Interaction):
    p = profile(interaction.guild_id, interaction.user.id); now = datetime.now(timezone.utc)
    if p["last_checkin"] and datetime.fromisoformat(p["last_checkin"]).date() == now.date(): await interaction.response.send_message("Você já fez check-in hoje."); return
    with db() as conn: conn.execute("UPDATE profiles SET balance=balance+100, last_checkin=? WHERE guild_id=? AND user_id=?", (now.isoformat(), interaction.guild_id, interaction.user.id))
    await interaction.response.send_message("✅ Check-in concluído: você recebeu **100 moedas**.")


@bot.tree.command(name="saldo", description="Mostra o saldo")
async def saldo(interaction: discord.Interaction, membro: discord.Member | None = None):
    member = membro or interaction.user; p = profile(interaction.guild_id, member.id)
    await interaction.response.send_message(f"💰 {member.mention} possui **{p['balance']}** moedas.")


@bot.tree.command(name="transferir", description="Transfere moedas")
async def transferir(interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 999999]):
    if membro.bot or membro.id == interaction.user.id: await interaction.response.send_message("Escolha outro membro."); return
    p = profile(interaction.guild_id, interaction.user.id)
    if p["balance"] < quantidade: await interaction.response.send_message("Saldo insuficiente."); return
    profile(interaction.guild_id, membro.id)
    with db() as conn:
        conn.execute("UPDATE profiles SET balance=balance-? WHERE guild_id=? AND user_id=?", (quantidade, interaction.guild_id, interaction.user.id))
        conn.execute("UPDATE profiles SET balance=balance+? WHERE guild_id=? AND user_id=?", (quantidade, interaction.guild_id, membro.id))
    await interaction.response.send_message(f"Transferidas **{quantidade}** moedas para {membro.mention}.")


@bot.tree.command(name="ranking", description="Mostra os mais ricos")
async def ranking(interaction: discord.Interaction):
    with db() as conn: rows = conn.execute("SELECT user_id, balance FROM profiles WHERE guild_id=? ORDER BY balance DESC LIMIT 10", (interaction.guild_id,)).fetchall()
    lines = [f"{pos}. <@{r['user_id']}> — **{r['balance']}**" for pos, r in enumerate(rows, 1)] or ["Ainda não há dados."]
    await interaction.response.send_message(embed=discord.Embed(title="🏆 Ranking", description="\n".join(lines), color=COLOR))


@bot.tree.command(name="sorteio_iniciar", description="[Admin] Inicia um sorteio")
@app_commands.check(admin_only)
async def sorteio_iniciar(interaction: discord.Interaction, premio: str, minutos: app_commands.Range[int, 1, 10080], vencedores: app_commands.Range[int, 1, 20] = 1):
    ends_at = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    with db() as conn:
        cursor = conn.execute("INSERT INTO giveaways (guild_id, channel_id, prize, winners, ends_at) VALUES (?, ?, ?, ?, ?)", (interaction.guild_id, interaction.channel_id, premio, vencedores, ends_at.isoformat()))
        giveaway_id = cursor.lastrowid
    view = GiveawayView(giveaway_id)
    await interaction.response.send_message(f"🎉 **SORTEIO: {premio}**\nTermina <t:{int(ends_at.timestamp())}:R> · {vencedores} vencedor(es).", view=view)
    message = await interaction.original_response()
    with db() as conn: conn.execute("UPDATE giveaways SET message_id=? WHERE id=?", (message.id, giveaway_id))
    bot.add_view(view); bot.schedule_giveaway(giveaway_id, ends_at.isoformat())


@bot.tree.command(name="sorteio_listar", description="Lista sorteios ativos")
async def sorteio_listar(interaction: discord.Interaction):
    with db() as conn: rows = conn.execute("SELECT * FROM giveaways WHERE guild_id=? AND ended=0 ORDER BY ends_at", (interaction.guild_id,)).fetchall()
    text = "\n".join(f"`#{r['id']}` {r['prize']} — termina <t:{int(datetime.fromisoformat(r['ends_at']).timestamp())}:R>" for r in rows) or "Nenhum sorteio ativo."
    await interaction.response.send_message(embed=discord.Embed(title="🎉 Sorteios ativos", description=text, color=COLOR))


@bot.tree.command(name="sorteio_encerrar", description="[Admin] Encerra um sorteio")
@app_commands.check(admin_only)
async def sorteio_encerrar(interaction: discord.Interaction, id: int):
    await interaction.response.send_message("Encerrando sorteio...")
    await finish_giveaway(id, bot)


@bot.tree.command(name="sorteio_rerolar", description="[Admin] Sorteia novos vencedores")
@app_commands.check(admin_only)
async def sorteio_rerolar(interaction: discord.Interaction, id: int):
    await interaction.response.send_message("Refazendo o sorteio...")
    await finish_giveaway(id, bot, reroll=True)


@bot.tree.command(name="dizer", description="[Admin] Envia uma mensagem como o bot")
@app_commands.check(admin_only)
async def dizer(interaction: discord.Interaction, mensagem: str):
    await interaction.response.send_message("Mensagem enviada.")
    await interaction.channel.send(mensagem)


@bot.tree.command(name="dizer_no_canal", description="[Admin] Envia uma mensagem em outro canal")
@app_commands.check(admin_only)
async def dizer_no_canal(interaction: discord.Interaction, canal: discord.TextChannel, mensagem: str):
    await canal.send(mensagem); await interaction.response.send_message("Mensagem enviada.")


@bot.tree.command(name="configurar_prefixo", description="[Admin] Define ou mostra o prefixo de comandos")
async def configurar_prefixo(interaction: discord.Interaction, prefixo: str | None = None):
    if prefixo is not None:
        if not is_admin(interaction): await interaction.response.send_message("Você precisa ser administrador."); return
        if len(prefixo) > 5: await interaction.response.send_message("Use no máximo 5 caracteres."); return
        with db() as conn: conn.execute("INSERT INTO settings (guild_id,prefix) VALUES (?,?) ON CONFLICT(guild_id) DO UPDATE SET prefix=excluded.prefix", (interaction.guild_id, prefixo))
        await interaction.response.send_message(f"Prefixo definido como `{prefixo}`."); return
    with db() as conn:
        row = conn.execute("SELECT prefix FROM settings WHERE guild_id=?", (interaction.guild_id,)).fetchone()
    await interaction.response.send_message(f"Prefixo atual: `{row['prefix'] if row else DEFAULT_PREFIX}`. Você pode usar tanto o prefixo quanto os comandos de barra (`/`).")


@bot.tree.command(name="olar", description="Cumprimenta o usuário")
async def olar(interaction: discord.Interaction): await interaction.response.send_message("Olá, mundo!")


@bot.tree.command(name="soco_azul", description="Dá um soco azul")
async def soco_azul(interaction: discord.Interaction, alvo: discord.Member):
    embed = discord.Embed(description=f"{interaction.user.mention} desfere um soco reforçado com energia amaldiçoada em azul contra {alvo.mention}!", color=COLOR)
    embed.set_image(url="https://i.ibb.co/Zp2RSVny/ezgif-com-video-to-gif-converter-1.gif")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="sequencia_golpes", description="Sequência de golpes")
async def sequencia_golpes(interaction: discord.Interaction, alvo: discord.Member):
    embed = discord.Embed(description=f"{interaction.user.mention} desfere uma sequência de golpes contra {alvo.mention}!", color=COLOR)
    embed.set_image(url="https://i.ibb.co/Hp21FQxD/ezgif-com-video-to-gif-converter-2.gif")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="black_flash", description="Tenta acertar um Black Flash")
async def black_flash(interaction: discord.Interaction, alvo: discord.Member):
    success = attempt_black_flash(interaction.guild_id, interaction.user.id)
    await interaction.response.send_message(embed=black_flash_embed(interaction.user, alvo, success))

@bot.tree.command(
    name="violence",
    description="Arremessa alguém pelos prédios."
)
async def violence(interaction: discord.Interaction, alvo: discord.Member):
    if interaction.user.id != BLACK_FLASH_USUARIO_GARANTIDO_ID:
        await interaction.response.send_message(
            "❌ Você não pode usar esse comando."
        )
        return

    if alvo.bot:
        await interaction.response.send_message(
            "Você não pode usar esse comando em bots."
        )
        return

    if alvo.id == interaction.user.id:
        await interaction.response.send_message(
            "Você não pode usar esse comando em si mesmo."
        )
        return

    await interaction.response.send_message(
        embed=violence_embed(interaction.user, alvo)
    )

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN não foi encontrado no arquivo .env")
bot.run(TOKEN)
