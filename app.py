# app.py
import os
import json
import random
from collections import defaultdict
from flask import Flask, render_template, request, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'very_secret_key_for_word_game'

# Пути к данным
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
NOUNS_PATH = os.path.join(DATA_DIR, 'nouns.txt')
BIGRAM_PATH = os.path.join(DATA_DIR, 'bigram_freq.json')

# Загрузка словаря
def load_nouns():
    if not os.path.exists(NOUNS_PATH):
        return {'кот', 'стол', 'лес', 'сон', 'нос', 'сок', 'код', 'дом', 'море', 'торт'}
    with open(NOUNS_PATH, 'r', encoding='utf-8') as f:
        return set(word.strip().lower() for word in f if word.strip())

# Загрузка частот биграмм
def load_bigram_freq():
    if os.path.exists(BIGRAM_PATH):
        with open(BIGRAM_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    # fallback: равномерная частота
    return {}

nouns = load_nouns()
bigram_freq = load_bigram_freq()

def get_bigrams(word):
    return [word[i:i+2] for i in range(len(word)-1)]

def score_word(word, bigram_freq):
    bigrams = get_bigrams(word)
    if not bigrams:
        return 0
    total = 0
    for bg in bigrams:
        freq = bigram_freq.get(bg, 0.0)
        total += 1 / (freq + 0.001)  # избегаем деления на 0
    return round(total, 2)

def get_last_two_letters(word):
    if len(word) >= 2:
        return word[-2:]
    elif len(word) == 1:
        return word
    else:
        return ""

@app.route('/')
def index():
    if 'used_words' not in session:
        # Начало игры: компьютер выбирает первое слово
        computer_word = random.choice(list(nouns))
        session['used_words'] = [computer_word]
        session['total_score'] = 0
        session['last_word'] = computer_word
    return render_template('index.html', last_word=session['last_word'])

@app.route('/submit', methods=['POST'])
def submit():
    player_word = request.form.get('word', '').strip().lower()
    if not player_word:
        flash('Введите слово!')
        return redirect(url_for('index'))

    # Базовые проверки
    if player_word not in nouns:
        flash('Слово не найдено в словаре.')
        return redirect(url_for('index'))

    if player_word in session['used_words']:
        flash('Это слово уже использовалось.')
        return redirect(url_for('index'))

    last_word = session['last_word']
    required_prefix = get_last_two_letters(last_word)
    actual_prefix = get_last_two_letters(player_word)

    # Проверка: нормальный ход (на две буквы)
    if len(required_prefix) == 2 and player_word.startswith(required_prefix):
        multiplier = 1.0
        valid = True
    # Аварийный ход: перестановка
    elif len(required_prefix) == 2 and player_word.startswith(required_prefix[::-1]):
        multiplier = 0.5
        valid = True
    # Аварийный ход: последняя буква
    elif len(required_prefix) >= 1 and player_word.startswith(required_prefix[-1]):
        multiplier = 0.25
        valid = True
    else:
        flash(f'Слово должно начинаться с "{required_prefix}" (или с перестановки / последней буквы).')
        return redirect(url_for('index'))

    if not valid:
        flash('Недопустимое слово.')
        return redirect(url_for('index'))

    # Расчёт баллов
    base_score = score_word(player_word, bigram_freq)
    final_score = round(base_score * multiplier, 2)

    # Обновление сессии
    session['used_words'].append(player_word)
    session['total_score'] += final_score
    session['last_word'] = player_word  # теперь это слово — для следующего хода (в полной игре)

    return render_template(
        'result.html',
        word=player_word,
        base_score=base_score,
        multiplier=multiplier,
        final_score=final_score,
        total_score=session['total_score']
    )

if __name__ == '__main__':
    app.run(debug=True)