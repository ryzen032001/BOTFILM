import os
import discord
from discord.ext import commands, tasks
import random
import requests
import datetime
import json  # Import library untuk bekerja dengan JSON
import asyncio
from github import Github


intents = discord.Intents.all()  # Enable all intents
bot = commands.Bot(command_prefix='!', intents=intents, owner_id=697422617518407779)
previous_movies = {}  # Dictionary untuk menyimpan ID film yang telah ditampilkan sebelumnya untuk setiap server
bot_channels = {}  # Dictionary untuk menyimpan ID saluran kerja bot untuk setiap server
bot_allowed_roles = {}  # Dictionary untuk menyimpan daftar ID peran yang diizinkan untuk setiap server

TMDB_API_KEY = '80a72b23fb1fd6d983c68a00959d0ab2'

# Ambil token GitHub dari variabel lingkungan
github_token = os.environ.get('GITHUB_TOKEN')

# Autentikasi dengan token GitHub
g = Github(github_token)

# Periksa apakah file data_bot.json ada dan muat data
if os.path.exists("data_bot.json"):
    with open("data_bot.json", "r") as file:
        data = json.load(file)
        
        # Dapatkan nilai untuk bot_allowed_roles, bot_channels, dan previous_movies
        bot_allowed_roles = {int(key): value for key, value in data.get("bot_allowed_roles", {}).items()}
        bot_channels = {int(key): value for key, value in data.get("bot_channels", {}).items()}
        previous_movies_serializable = data.get("previous_movies", {})
        
        # Konversi kembali list menjadi set
        previous_movies = {int(server_id): set(movie_ids) for server_id, movie_ids in previous_movies_serializable.items()}
else:
    bot_allowed_roles = {}
    bot_channels = {}
    previous_movies = {}

    

# Fungsi untuk menyimpan data ke dalam file JSON saat bot dimatikan
def save_data():

    repo_owner = 'ryzen032001'
    repo_name = 'BOTFILM'
    repo = g.get_user(repo_owner).get_repo(repo_name)

    # Konversi set menjadi list sebelum menyimpan ke JSON
    previous_movies_serializable = {str(server_id): list(movie_ids) for server_id, movie_ids in previous_movies.items()}
    data = {
        "bot_allowed_roles": bot_allowed_roles,
        "bot_channels": bot_channels,
        "previous_movies": previous_movies_serializable  # Tambahkan previous_movies ke data yang akan disimpan
    }

    file_path = "data_bot.json"
    file_content = json.dumps(data, indent=4)  # Isi file JSON yang ingin Anda tulis atau ubah

    try:
        # Mencoba untuk mengambil konten file yang ada
        contents = repo.get_contents(file_path)
        repo.update_file(contents.path, "Update data", file_content, contents.sha)
    except Exception as e:
        # Jika file tidak ada, membuat file baru
        repo.create_file(file_path, "Create data", file_content)


@bot.command()
async def set_allowed_roles(ctx, *roles: discord.Role):
    # Memeriksa apakah pengguna adalah administrator
    if ctx.message.author.guild_permissions.administrator:
        # Menyimpan daftar ID peran yang diizinkan untuk server tertentu
        server_id = ctx.guild.id
        bot_allowed_roles[server_id] = [role.id for role in roles]
        await ctx.send(f"Peran yang diizinkan telah diatur.")
        save_data()
    else:
        await ctx.send("Anda tidak memiliki izin untuk menggunakan perintah ini.")
# Perintah untuk mengecek role yang diizinkan untuk mengatur bot
@bot.command()
async def check_allowed_roles(ctx):
    server_id = ctx.guild.id
    allowed_roles = bot_allowed_roles.get(server_id)
    if allowed_roles:
        role_mentions = [ctx.guild.get_role(role_id).mention for role_id in allowed_roles]
        await ctx.send(f"Role yang diizinkan untuk mengatur bot: {', '.join(role_mentions)}")
    else:
        await ctx.send("Tidak ada role yang diizinkan untuk mengatur bot di server ini.")

@bot.command()
async def set_channel(ctx):
    is_admin = ctx.message.author.guild_permissions.administrator
    is_owner = ctx.message.author.id == bot.owner_id
    
    # Memeriksa apakah pengguna adalah admin, pemilik bot, atau memiliki salah satu peran yang diizinkan
    if is_admin or is_owner or any(role.id in bot_allowed_roles.get(ctx.guild.id, []) for role in ctx.author.roles):
        channel = ctx.message.channel
        server_id = ctx.guild.id
        
        # Memeriksa apakah saluran kerja bot sudah diatur sebelumnya di server ini
        if bot_channels.get(server_id) is not None:
            await ctx.send("Saluran kerja bot sudah diatur di server ini.")
            return
        
        # Jika belum, atur saluran kerja bot
        bot_channels[server_id] = channel.id
        previous_movies[server_id] = set()  # Membuat set kosong untuk server yang baru
        await ctx.send(f"Saluran kerja bot telah diatur ke {channel.name}")
        save_data()
    else:
        await ctx.send("Anda tidak memiliki izin untuk menggunakan perintah ini.")

@bot.command()
async def change_channel(ctx):
    is_admin = ctx.message.author.guild_permissions.administrator
    is_owner = ctx.message.author.id == bot.owner_id
    
    # Memeriksa apakah pengguna adalah admin, pemilik bot, atau memiliki salah satu peran yang diizinkan
    if is_admin or is_owner or any(role.id in bot_allowed_roles.get(ctx.guild.id, []) for role in ctx.author.roles):
        channel = ctx.message.channel
        server_id = ctx.guild.id
        
        # Memeriksa apakah saluran kerja bot sudah diatur sebelumnya di server ini
        if bot_channels.get(server_id) is not None:
            # Jika sudah diatur sebelumnya, ganti saluran kerja bot
            bot_channels[server_id] = channel.id
            await ctx.send(f"Saluran kerja bot telah diubah ke {channel.name}")
            save_data()
        else:
            # Jika belum diatur sebelumnya, beri tahu pengguna untuk menggunakan perintah !set_channel
            await ctx.send("Saluran kerja bot belum diatur di server ini. Silakan gunakan perintah !set_channel untuk mengatur saluran kerja bot.")
    else:
        await ctx.send("Anda tidak memiliki izin untuk menggunakan perintah ini.")

@bot.command()
async def check_channel(ctx):
    server_id = ctx.guild.id
    channel_id = bot_channels.get(server_id)
    if channel_id is not None:
        channel = bot.get_channel(channel_id)
        if channel:
            await ctx.send(f"Bot saat ini bekerja di saluran {channel.name}.")
        else:
            await ctx.send("Saluran tidak ditemukan.")
    else:
        await ctx.send("Bot belum diatur untuk bekerja di saluran manapun.")



def get_now_playing_movies(api_key):
    try:
        url = f'https://api.themoviedb.org/3/movie/now_playing?api_key={api_key}&language=id-ID&page=1'
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('results', [])
    except requests.exceptions.RequestException as e:
        print("Failed to fetch data from TMDb API:", e)
        return []

def get_movie_image(movie_id, api_key):
    try:
        url = f'https://api.themoviedb.org/3/movie/{movie_id}/images?api_key={api_key}'
        response = requests.get(url)
        response.raise_for_status()
        images = response.json().get('posters', [])
        if images:
            return f"http://image.tmdb.org/t/p/w500/{images[0]['file_path']}"  # Mengambil URL gambar pertama
        else:
            return None
    except requests.exceptions.RequestException as e:
        print("Failed to fetch image data from TMDb API:", e)
        return None

@bot.command(name='recommend')
async def recommend_movie(ctx):
    movies = get_now_playing_movies(TMDB_API_KEY)
    if movies:
        recommended_movie = random.choice(movies)
        movie_title = recommended_movie.get('title', 'Unknown')
        movie_id = recommended_movie.get('id')
        movie_image_url = get_movie_image(movie_id, TMDB_API_KEY)
        movie_overview = recommended_movie.get('overview', 'No synopsis available.')
        
        if movie_image_url:
            embed = discord.Embed(title=f"Recommended Movie: {movie_title}", description=movie_overview, color=0x00ff00)
            embed.set_image(url=movie_image_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"I recommend the movie: {movie_title}\nSynopsis: {movie_overview}")
    else:
        await ctx.send("Sorry, unable to find movie recommendations at the moment.")

# Fungsi untuk mengambil daftar genre film dari API TMDb
def get_movie_genres(api_key):
    try:
        url = f'https://api.themoviedb.org/3/genre/movie/list?api_key={api_key}&language=id-ID'
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('genres', [])
    except requests.exceptions.RequestException as e:
        print("Failed to fetch data from TMDb API:", e)
        return []

# Fungsi untuk mengambil daftar film berdasarkan genre dari API TMDb
def get_movies_by_genre(api_key, genre_id):
    try:
        url = f'https://api.themoviedb.org/3/discover/movie?api_key={api_key}&language=id-ID&sort_by=popularity.desc&include_adult=false&include_video=false&page=1&with_genres={genre_id}'
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('results', [])
    except requests.exceptions.RequestException as e:
        print("Failed to fetch data from TMDb API:", e)
        return []

@bot.command()
async def recommend_genre(ctx, genre_name):
    # Mendapatkan ID genre film berdasarkan nama genre yang diinput
    genres = get_movie_genres(TMDB_API_KEY)
    genre_id = None
    for genre in genres:
        if genre['name'].lower() == genre_name.lower():
            genre_id = genre['id']
            break

    if genre_id is not None:
        # Mendapatkan daftar film berdasarkan genre yang dipilih
        movies = get_movies_by_genre(TMDB_API_KEY, genre_id)
        if movies:
            await ctx.send(f"Film berdasarkan genre {genre_name}:")
            for movie in movies:
                movie_title = movie.get('title', 'Unknown')
                movie_poster_path = movie.get('poster_path')
                movie_overview = movie.get('overview', 'Tidak ada sinopsis yang tersedia.')
                
                if movie_poster_path:
                    movie_image_url = f"http://image.tmdb.org/t/p/w500/{movie_poster_path}"
                    embed = discord.Embed(title=movie_title, description=movie_overview, color=0x00ff00)
                    embed.set_image(url=movie_image_url)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"**{movie_title}**\n{movie_overview}")
        else:
            await ctx.send("Maaf, tidak dapat menemukan film untuk genre yang dipilih.")
    else:
        await ctx.send("Maaf, genre yang dimasukkan tidak valid.")

@bot.command()
async def list_genres(ctx):
    genres = get_movie_genres(TMDB_API_KEY)
    if genres:
        genre_list = ", ".join(genre['name'] for genre in genres)
        await ctx.send(f"Daftar genre film yang tersedia: {genre_list}")
    else:
        await ctx.send("Maaf, tidak dapat menemukan daftar genre saat ini.")

@bot.command()
async def show_help(ctx):
    help_message = """
    **Daftar Command:**
    '!set_allowed_role' : admin dapat mengizinkan 1 role yang bisa ikut mengatur bot selain admin
    '!check_allowed_role' : melihat role yang diizinkan untuk mengatur bot
    `!set_channel`: Memilih channel yang akan di tangani oleh bot.
    `!change_channel`: Mengganti channel yang akan di tangani oleh bot.
    `!check_channel` : melihat channel yang di tangani oleh bot.
    `!recommend`: Menampilkan film yang direkomendasikan secara random.
    `!recommend_genre [nama genre]`: Menampilkan daftar film berdasarkan genre.
    `!list_genres`: Menampilkan daftar genre film yang tersedia.
    `!help`: Menampilkan daftar command yang tersedia.
    """
    await ctx.send(help_message)



# Function untuk mengirim film terbaru ke saluran
async def send_now_playing_movies(server_id):
    global previous_movies, bot_channels
    channel_id = bot_channels.get(server_id)
    if channel_id is not None:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                url = f'https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_API_KEY}&language=id-ID&page=1'
                response = requests.get(url)
                response.raise_for_status()
                movies = response.json().get('results', [])
                if movies:
                    for movie in movies:
                        movie_id = movie.get('id')
                        if server_id not in previous_movies:  
                            previous_movies[server_id] = set()  
                        if movie_id not in previous_movies[server_id]:
                            movie_title = movie.get('title', 'Unknown')
                            movie_release_date = movie.get('release_date', 'Unknown')
                            movie_poster_path = movie.get('poster_path')
                            movie_overview = movie.get('overview', 'Tidak ada sinopsis yang tersedia.')
                            if movie_poster_path:
                                movie_image_url = f"http://image.tmdb.org/t/p/w500/{movie_poster_path}"
                                embed = discord.Embed(title=f"{movie_title} (Rilis: {movie_release_date})", description=movie_overview, color=0x00ff00)
                                embed.set_image(url=movie_image_url)
                                await channel.send(embed=embed)
                            else:
                                await channel.send(f"**{movie_title}** (Rilis: {movie_release_date})\n{movie_overview}")
                            previous_movies[server_id].add(movie_id)
                            save_data()
                else:
                    await channel.send("Maaf, tidak dapat menemukan informasi film terbaru saat ini.")
            except requests.exceptions.RequestException as e:
                print("Failed to fetch data from TMDb API:", e)
                await channel.send("Maaf, tidak dapat mengambil data dari API saat ini.")
        else:
            print("Saluran tidak ditemukan.")
    else:
        print("Saluran kerja bot belum diatur untuk server ini.")



# Perintah untuk menampilkan film terbaru yang sedang tayang
@bot.command()
async def now_playing_movies(ctx):
    server_id = ctx.guild.id
    await send_now_playing_movies(server_id)

@bot.event
async def on_ready():
    print('Bot is ready.')
    daily_now_playing_movies.start()

# Task untuk menjalankan perintah now_playing_movies setiap 6 jam
@tasks.loop(hours=1)
async def daily_now_playing_movies():
    now = datetime.datetime.now()
    print(f"Running now_playing_movies at {now}")
    for server_id in bot_channels:
        await send_now_playing_movies(server_id)

@daily_now_playing_movies.before_loop
async def before_daily_now_playing_movies():
    await bot.wait_until_ready()

@bot.command()
@commands.is_owner()
@commands.dm_only()  # Hanya bisa dipicu melalui pesan pribadi
async def maintenance(ctx, *, message: str = "Maintenance will start in 3 minutes."):
    # Mengecek apakah perintah dipicu dari pesan pribadi
    if ctx.guild is None:
        # Jika dipicu dari pesan pribadi, kirim pengumuman ke semua server
        for server_id, channel_id in bot_channels.items():
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(f"🛠️ **Maintenance Notice:** {message}")
            else:
                print(f"Failed to find the designated channel for server ID {server_id}.")
        await ctx.send("Maintenance notice has been sent to all server channels.")
        #Menghitung mundur selama 3 menit
        await asyncio.sleep(180)
    
        # Mematikan bot
        await bot.close()
        




@bot.event
async def on_disconnect():
    save_data()

bot.run(os.environ["DISCORD_TOKEN"])
