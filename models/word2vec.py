import pandas as pd
from gensim.models.keyedvectors import KeyedVectors
import re
from nltk.corpus import stopwords
from nltk import download
import stanza

from process_data.dictionary import get_dictionary

class W2v():
    def __init__(self):
        # stanza.download("sv")
        # stemmer = SnowballStemmer("swedish")
        # download('stopwords')  # Download stopwords list.
        self.ur_df = pd.read_csv("massive_data/stored_data/search_ur_cleaned.csv", engine='python')
        self.word_vectors = KeyedVectors.load('massive_data/word_vector_models/coNLL17_vectors.kv')
        self.nlp = stanza.Pipeline("sv", processors='tokenize,lemma')

        self.dictionary = get_dictionary()

    def generate_id(self):
        random_row = self.ur_df.sample()
        return random_row.iloc[0]['~uid'].strip('~')

    def find_CI(self, chosen_uid):
        chosen_uid = f'~{chosen_uid}'
        self.chosen_content = self.ur_df[self.ur_df['~uid'] == chosen_uid]

        self.content_id = chosen_uid.strip('~')
        self.title = self.chosen_content.iloc[0]['title']
        self.surtitle = self.chosen_content.iloc[0]['surtitle']
        self.thumbnail = self.chosen_content.iloc[0]['thumbnail']
        self.keywords = self.chosen_content.iloc[0]['keywords~']
        self.keywords = self.keywords.strip(',~')
        self.description = self.chosen_content.iloc[0]['description']
        self.subject = self.chosen_content.iloc[0]['subject'] 
        self.audience = self.chosen_content.iloc[0]['audience']

        CI = pd.read_csv('massive_data/stored_data/CI_vocab.csv')
        CIT = pd.read_csv('massive_data/stored_data/CI_vocab_including_titles.csv')


        self.CI_current = CI[CI['subject'].isin(self.subject.split(', ')) & CI['audience'].isin(self.audience.split(', '))]
        self.CI_currentT = CIT[CIT['subject'].isin(self.subject.split(', ')) & CIT['audience'].isin(self.audience.split(', '))]  


    def preprocess_texts(self, text):
        stop_words = stopwords.words('swedish')
        text = text.lower()
        text = ' '.join([self.dictionary.get(i, i) for i in text.split()])
        text = re.sub(r"[^\w\d'\s\-]+", '', text)
        text = " ".join([w for w in text.split() if w not in stop_words])
        return text.split(" ")

    def cos_sim(self, keywords, CI_doc):         
        try:
            similarity = self.word_vectors.n_similarity(keywords, CI_doc)
            return similarity
        except KeyError as e:
            error_code = e.args[0].split()
            error_term = error_code[1].strip("'")
            if error_term in CI_doc:
                CI_doc.remove(error_term)
            if error_term in keywords:
                keywords.remove(error_term) 
            results = self.cos_sim(keywords, CI_doc)
        if results: 
            return results

    def wmd(self, keywords, CI_doc):
        try:
            distance = self.word_vectors.wmdistance(keywords, CI_doc)
            return distance
        except KeyError as e:
            error_code = e.args[0].split()
            error_term = error_code[1].strip("'")
            if error_term in CI_doc:
                CI_doc.remove(error_term)
            if error_term in keywords:
                keywords.remove(error_term) 
            results = self.wmd(keywords, CI_doc)
        if results: 
            return results

    def predict_CI(self, model, uid):
        self.find_CI(uid)

        CI_keywords_dict = {}

        if not isinstance(self.surtitle, float):
            keywords_titles = self.keywords + ', ' + self.title + ', ' + self.surtitle

        else:
            keywords_titles = self.keywords + ', ' + self.title

        content_processed_titles = self.preprocess_texts(keywords_titles)
        content_processed = self.preprocess_texts(self.keywords)

        if model == 'cos sim':
            for i, row in self.CI_current.iterrows():
                CI_processed = self.preprocess_texts(row['value'])
                result = self.cos_sim(content_processed, CI_processed)
                formatted_string = "{:.3f}".format(result)
                result = float(formatted_string)
                CI_keywords_dict[row['uuid']] = {'CI': row['CI'], 'title':  row['title'], 'value': result}
        elif 'titles' in model:
            for i, row in self.CI_currentT.iterrows():
                CI_processed = self.preprocess_texts(row['value'])
                result = self.cos_sim(content_processed_titles, CI_processed)
                formatted_string = "{:.3f}".format(result)
                result = float(formatted_string)
                CI_keywords_dict[row['uuid']] = {'CI': row['CI'], 'title':row['title'], 'value': result}

        if 'cos' in model:
            sorted_dict = sorted(CI_keywords_dict.items(), reverse=True, key = lambda x: x[1]['value'])
            top_candidates = []
            memory = []
            i = 0
            while len(top_candidates) < 3:
                if (sorted_dict[i][1].get('CI')) not in memory:
                    top_candidates.append(sorted_dict[i])
                    memory.append(sorted_dict[i][1].get('CI'))
                i += 1
            for key in sorted_dict:
                top_id = []
                for value in top_candidates:
                    top_id.append(value[0])
                if(key[1].get('value') > 0.87) and (key[0] not in top_id):
                    top_candidates.append(key)
        # elif data == 'wmd':
        #     sorted_dict = sorted(CI_keywords_dict.items(), reverse=False, key = lambda x: x[1]['value'])
        #     top_candidates = sorted_dict[0:3]
        #     for key in sorted_dict:
        #         top_id = []
        #         for value in top_candidates:
        #             top_id.append(value[0])
        #         if(key[1].get('value') < 0.95) and (key[0] not in top_id):
        #             top_candidates.append(key)

        # for elem in sorted_dict:
        #     print(f'{elem[0]} : {elem[1]*100} %')  
        return top_candidates 







