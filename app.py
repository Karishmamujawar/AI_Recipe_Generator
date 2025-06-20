import os
import cohere
import requests
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template,redirect, url_for, make_response,session
from urllib.parse  import quote 
from datetime import datetime
import pdfkit
import platform
from deep_translator import GoogleTranslator


app = Flask(__name__)

app.secret_key = "your_secret_key "


# Replace with your actual Cohere API key
co = cohere.Client("akFvSkDUZDmz6twdXA40QGWNB1PIDRKb78gJAlF5")
PEXELS_API_KEY = "AI51PNQEzvs28jZoSNyMm4BpHYnnt47C3WOCDpLyF4lzRfPbziqOo2xZ"     # Replace with your Pexels API key


#database : SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


#For pdf donwnload
if platform.system() == 'Windows':
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
else:
    path_wkhtmltopdf = '/usr/bin/wkhtmltopdf'
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)


#Model
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ingredients  = db.Column(db.Text, nullable=False)
    cook_time = db.Column(db.String(20))
    preferences = db.Column(db.String(100))
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    def __init__(self,ingredients,cook_time,preferences,content,image_url):
        self.ingredients = ingredients
        self.cook_time = cook_time
        self.preferences = preferences
        self.content = content
        self.image_url = image_url




@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        ingredients = request.form['ingredients']
        preferences = request.form.getlist('diet')  # Get list of selected checkboxes
        cook_time = request.form['cook_time'] 
        preference_text  = ", ".join(preferences)    # Add dietary preference to prompt
        # language = request.form['language']

        content = generate_recipe(ingredients,preference_text,cook_time)
        image_url = fetch_image(content)

        #save to db
        new_recipe = Recipe(ingredients=ingredients, cook_time=cook_time, preferences=preference_text,content=content,image_url=image_url)
        db.session.add(new_recipe)
        db.session.commit()

        return redirect(url_for('view_recipe', recipe_id=new_recipe.id))
        # return render_template('result.html', ingredients=ingredients, response=recipe_text, image_url=image_url )
    return render_template('index.html')


#view Page
@app.route('/recipe/<int:recipe_id>')
def view_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    prev = Recipe.query.filter(Recipe.id < recipe_id).order_by(Recipe.id.desc()).first()
    next = Recipe.query.filter(Recipe.id > recipe_id).order_by(Recipe.id.asc()).first()
    return render_template('/result.html', recipe=recipe, prev=prev, next=next) 


#Cohere Recipe generator
def generate_recipe(ingredients,preferences,cook_time):
    preferences_part = f"The recipe should follow these dietary preferences: {preferences}." if preferences else ""
    prompt = (
                f"Generate a recipe using the following ingredients: {ingredients}.Keep the total cooking time under {cook_time} minutes."
                f"Include a title, dish name,ingredients list, steps, and cooking time."
            )
    #Generate the entire recipe in {language}

    response = co.generate(
        model='command-r-plus', 
        prompt=prompt,
        max_tokens=400,
        temperature=0.8
    )

    return response.generations[0].text.strip()

    
#image feching
def fetch_image(content):
    title = content.split('\n')[0].strip("# ").strip()
    query = quote(title)

    headers = {
         "Authorization" : PEXELS_API_KEY
     }

    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    response = requests.get(url, headers=headers)

    # print("KEY PRESENT:", bool(PEXELS_API_KEY))
    # print(requests.get(url, headers=headers).text)


    if response.status_code == 200:
        data = response.json()
        if data["photos"]:
            return data["photos"][0]["src"]["medium"]

    else:
        print(f"Pexels Error: {response.status_code}, {response.text}")
    
    return None



#Download option
@app.route('/download/<int:recipe_id>',  methods=['GET'])
def download_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    
    #Get language from query string
    target_lang = request.args.get('language', 'english')
    

    lang_map = {
        'english' : 'en',  
        'hindi' : 'hi',
        'tamil' : 'ta',
        'telugu' : 'te',
        'kannada' : 'kn'
    }

    translated_content = recipe.content
    translated_preferences = recipe.preferences

    if target_lang in lang_map:
        target_code = lang_map[target_lang]
       
        
        translated_content = GoogleTranslator(source='auto', target=target_code).translate(recipe.content)
        translated_preferences = GoogleTranslator(source='auto', target=target_code).translate(recipe.preferences)
        
    

    rendered = render_template("result.html", recipe=recipe,translated_content=translated_content, translated_preferences=translated_preferences, image_url = recipe.image_url)
    
    options = {
        'encoding': "UTF-8",
        'no-outline': None,
        'enable-local-file-access': None,
        'quiet': '',
        }  
    
    pdf = pdfkit.from_string(rendered, False,configuration=config,options=options)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf' 
    response.headers['Content-Disposition'] = f'attachment; filename=recipe_{recipe.id}_{target_lang}.pdf'

    return response


#Translate recipe
@app.route('/translate/<int:recipe_id>' , methods=['POST'])
def translate_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    prev = Recipe.query.filter(Recipe.id < recipe_id).order_by(Recipe.id.desc()).first()
    next = Recipe.query.filter(Recipe.id > recipe_id).order_by(Recipe.id.asc()).first()

    target_lang = request.form['language']
    session['language'] = target_lang

    lang_map = {
        'english' : 'en',  #these are the in built translated code
        'hindi' : 'hi',
        'tamil' : 'ta',
        'telugu' : 'te',
        'kannada' : 'kn'
    }

    if target_lang in lang_map:
        target_code = lang_map[target_lang]

        try:
            translated_content =  GoogleTranslator(source='auto' , target=target_code).translate(recipe.content)
            translated_preferences = GoogleTranslator(source='auto', target =target_code).translate(recipe.preferences)


        except Exception as e:
            print('Translate went wrong')  
            translated_content = recipe.content
            translated_preferences = recipe.preferences
    
    else:
        translated_content = recipe.content
        translated_preferences = recipe.preferences


    return render_template("result.html", recipe=recipe, prev=prev, next=next, translated_content=translated_content, translated_preferences=translated_preferences, selected_lang=target_lang)




#View all recipes
@app.route('/viewallrecipes', methods=['GET'])
def viewAll():
    recipe = Recipe.query.order_by(Recipe.created_at.desc()).all()
    return render_template('viewall.html', recipes = recipe)



# @app.route('/test_translate')
# def test_translate():
#     translated = GoogleTranslator(source='auto', target='kn').translate("Hello, how are you?")
#     return translated





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)