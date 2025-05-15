import pandas as pd
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

# Initialize Sentence-BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

def process_reviews(reviews):
    """Vectorize reviews and return the average vector."""
    if reviews:
        review_list = reviews.split(',')
        review_vectors = model.encode(review_list)
        return review_vectors.mean(axis=0)
    return None

def process_search(search):
    """Vectorize search queries and return the average vector."""
    if search:
        search_list = search.split(',')
        search_vectors = model.encode(search_list)
        return search_vectors.mean(axis=0)
    return None

def combine_product_with_reviews(product_data):
    """Combine product metadata and reviews to generate a vector."""
    combined_text = (
        f"Product Name: {product_data['name']}, "
        f"Rating: {product_data['rating']}, "
        f"Type: {product_data['type']}, "
        f"Gender: {product_data['gender']}, "
        f"Brand: {product_data['brand']}, "
        f"Description: {product_data['description']}"
    )
    product_vector = model.encode(combined_text)
    review_vector = process_reviews(product_data['reviews'])
    return product_vector + review_vector if review_vector is not None else product_vector

def vectorize_product_with_reviews(df):
    """Vectorize all products in the dataframe."""
    return [combine_product_with_reviews(product) for _, product in df.iterrows()]

def combine_user_with_search(user_data):
    """Combine user metadata, viewed products, and search history."""
    viewed_products = user_data['product'].split(',') if user_data['product'] else []
    product_text = ' '.join(viewed_products)
    combined_text = (
        f"user_id: {user_data['user_id']}, "
        f"viewed_products: {product_text}"
    )
    user_vector = model.encode(combined_text)
    search_vector = process_search(user_data['search'])
    return user_vector + search_vector if search_vector is not None else user_vector

def vectorize_user_with_search(df):
    """Vectorize all users in the dataframe."""
    return [combine_user_with_search(user) for _, user in df.iterrows()]

def recommend_product(user_vector, product_vectors, product_ids, top_n=12):
    """Recommend top_n products based on cosine similarity."""
    if len(product_vectors) == 0 or len(user_vector) == 0:
        return []
    
    # Convert to tensors
    user_vector = torch.tensor(user_vector).unsqueeze(0)
    product_vectors = torch.tensor(np.array(product_vectors))
    
    # Compute cosine similarity
    similarities = torch.nn.functional.cosine_similarity(user_vector, product_vectors)
    
    # Get top_n indices
    top_indices = similarities.argsort(descending=True)[:top_n]
    
    # Return product IDs and similarity scores
    return [(product_ids[i], similarities[i].item()) for i in top_indices]