# This example requires the 'message_content' privileged intents

import os
import discord
from discord.ext import commands, tasks
import random
import requests
import datetime



intents = discord.Intents.all()  # Enable all intents
bot = commands.Bot(command_prefix='!', intents=intents)
previous_movies = set()  # Set untuk menyimpan ID film yang telah ditampilkan sebelumnya

YOUR_CHANNEL_ID = None



# Perintah untuk mengatur saluran kerja bot
@bot.command()
async def set_channel(ctx):
    global YOUR_CHANNEL_ID
    if ctx.message.author.guild_permissions.administrator:
        # Menggunakan saluran tempat perintah diberikan sebagai saluran kerja bot
        channel = ctx.message.channel
        YOUR_CHANNEL_ID = channel.id  # Simpan ID saluran
        await ctx.send(f"Saluran kerja bot telah diatur ke {channel.name}")
    else:
        await ctx.send("Anda tidak memiliki izin untuk menggunakan perintah ini.")
@bot.command()
async def check_channel(ctx):
    global YOUR_CHANNEL_ID
    current_channel = bot.get_channel(YOUR_CHANNEL_ID)
    if current_channel:
        await ctx.send(f"Bot saat ini bekerja di saluran {current_channel.name}.")
    else:
        await ctx.send("Bot belum diatur untuk bekerja di saluran manapun.")

TMDB_API_KEY = '80a72b23fb1fd6d983c68a00959d0ab2'

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
    `!set_channel`: Memilih channel yang akan di tangani oleh bot.
    `!check_channel` : melihat channel yang di tangani oleh bot.
    `!recommend`: Menampilkan film yang direkomendasikan secara random.
    `!recommend_genre [nama genre]`: Menampilkan daftar film berdasarkan genre.
    `!list_genres`: Menampilkan daftar genre film yang tersedia.
    `!help`: Menampilkan daftar command yang tersedia.
    """
    await ctx.send(help_message)


# Fungsi untuk mendapatkan informasi film terbaru dan mengirimkannya ke saluran kerja bot
async def send_now_playing_movies():
    global YOUR_CHANNEL_ID
    global previous_movies
    if YOUR_CHANNEL_ID is not None:
        channel = bot.get_channel(YOUR_CHANNEL_ID)
        if channel:
            try:
                url = f'https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_API_KEY}&language=id-ID&page=1'
                response = requests.get(url)
                response.raise_for_status()
                movies = response.json().get('results', [])
                if movies:
                    for movie in movies:
                        movie_id = movie.get('id')
                        if movie_id not in previous_movies:  # Memeriksa apakah film sudah pernah ditampilkan sebelumnya
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
                            previous_movies.add(movie_id)  # Menambahkan ID film ke set film yang telah ditampilkan sebelumnya
                else:
                    await channel.send("Maaf, tidak dapat menemukan informasi film terbaru saat ini.")
            except requests.exceptions.RequestException as e:
                print("Failed to fetch data from TMDb API:", e)
                await channel.send("Maaf, tidak dapat mengambil data dari API saat ini.")
        else:
            print("Saluran tidak ditemukan.")
    else:
        print("Saluran kerja bot belum diatur.")

# Perintah untuk menampilkan film terbaru yang sedang tayang
@bot.command()
async def now_playing_movies(ctx):
    await send_now_playing_movies()

@bot.event
async def on_ready():
    print('Bot is ready.')
    daily_now_playing_movies.start()

# Task untuk menjalankan perintah now_playing_movies setiap 24 jam
@tasks.loop(hours=1)
async def daily_now_playing_movies():
    now = datetime.datetime.now()
    print(f"Running now_playing_movies at {now}")
    await send_now_playing_movies()

@daily_now_playing_movies.before_loop
async def before_daily_now_playing_movies():
    await bot.wait_until_ready()


bot.run(os.environ["DISCORD_TOKEN"])
