import numpy as np
from sentence_transformers import SentenceTransformer
from .models import Product, UserProfile, Review, SearchHistory, ViewHistory

# Initialize Sentence-BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

def process_reviews(product):
    """Vectorize all reviews for a product and return the average vector."""
    reviews = Review.objects.filter(product=product)
    if reviews.exists():
        review_texts = [review.description for review in reviews]
        review_vectors = model.encode(review_texts, convert_to_numpy=True)
        return review_vectors.mean(axis=0)
    return None  # No reviews available

def process_search(user_profile):
    """Vectorize all search queries for a user and return the average vector."""
    searches = SearchHistory.objects.filter(user=user_profile)
    if searches.exists():
        search_texts = [search.query for search in searches]
        search_vectors = model.encode(search_texts, convert_to_numpy=True)
        return search_vectors.mean(axis=0)
    return None  # No searches available

def combine_product_with_reviews(product):
    """Combine product metadata and reviews to generate a combined vector."""
    combined_text = (
        f"Product Name: {product.name}, Rating: {product.rating}, "
        f"Type: {product.type or 'Unknown'}, "
        f"Description: {product.description}"
    )
    
    product_vector = model.encode(combined_text, convert_to_numpy=True)
    review_vector = process_reviews(product)
    
    if review_vector is not None:
        combined_vector = product_vector + review_vector  # Combine vectors
    else:
        combined_vector = product_vector  # Use only product vector if no reviews
    
    # Save vector to product.vector_data
    product.vector_data = combined_vector.tolist()
    product.save()
    
    return product.id, product.name, combined_vector

def vectorize_product_with_reviews():
    """Vectorize all products and their reviews, updating vector_data."""
    products = Product.objects.all()
    product_vectors = []
    for product in products:
        product_id, product_name, vector = combine_product_with_reviews(product)
        product_vectors.append((product_id, product_name, vector))
    return product_vectors

def combine_user_with_search(user_profile):
    """Combine user metadata and search history to generate a combined vector."""
    # Use username and viewed products (from ViewHistory) as metadata
    viewed_products = ViewHistory.objects.filter(user=user_profile)
    viewed_text = " ".join([view.product.name for view in viewed_products]) if viewed_products.exists() else ""
    combined_text = f"User: {user_profile.user.username}, Viewed Products: {viewed_text}"
    
    user_vector = model.encode(combined_text, convert_to_numpy=True)
    search_vector = process_search(user_profile)
    
    if search_vector is not None:
        combined_vector = user_vector + search_vector  # Combine vectors
    else:
        combined_vector = user_vector  # Use only user vector if no searches
    
    # Save vector to user_profile.vector_data
    user_profile.vector_data = combined_vector.tolist()
    user_profile.save()
    
    return user_profile.user.id, user_profile.user.username, combined_vector

def vectorize_user_with_search():
    """Vectorize all users and their search histories, updating vector_data."""
    users = UserProfile.objects.all()
    user_vectors = []
    for user_profile in users:
        user_id, username, vector = combine_user_with_search(user_profile)
        user_vectors.append((user_id, username, vector))
    return user_vectors