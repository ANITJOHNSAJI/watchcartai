import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from django.core.exceptions import ObjectDoesNotExist
from .models import Product, UserProfile

# Initialize the SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

def recommend_product(user_input, user=None, top_n=3):
    """
    Recommend products based on user input text or user profile vector.

    Args:
        user_input (str): Text input (e.g., search query or description).
        user (User, optional): Django User object for personalized recommendations.
        top_n (int): Number of products to recommend (default: 3).

    Returns:
        list: List of tuples (product_id, product_name, similarity_score) for top_n products.
    """
    # Encode user input
    if isinstance(user_input, str) and user_input.strip():
        user_vector = model.encode(user_input, convert_to_tensor=True)
    elif user:  # Use UserProfile vector_data if user is provided and input is empty
        try:
            user_profile = UserProfile.objects.get(user=user)
            if user_profile.vector_data:
                user_vector = torch.tensor(user_profile.vector_data, dtype=torch.float32)
            else:
                return []  # No vector data available
        except ObjectDoesNotExist:
            return []  # UserProfile not found
    else:
        return []  # Invalid input

    # Fetch all products with vector_data
    products = Product.objects.exclude(vector_data__isnull=True)
    if not products.exists():
        return []  # No products with vector data

    # Extract product IDs, names, and vectors
    product_ids = []
    product_names = []
    product_vectors = []
    for product in products:
        if product.vector_data:  # Ensure vector_data is not empty
            product_ids.append(product.id)
            product_names.append(product.name)
            product_vectors.append(product.vector_data)

    if not product_vectors:
        return []  # No valid vectors

    # Convert product vectors to tensor
    product_vectors = torch.tensor(product_vectors, dtype=torch.float32)

    # Compute cosine similarities
    similarities = util.cos_sim(user_vector, product_vectors)

    # Convert similarities to NumPy array
    similarity_scores = similarities[0].cpu().numpy()

    # Sort products by similarity
    sorted_indices = np.argsort(similarity_scores)[::-1][:top_n]

    # Prepare recommended products
    recommended_products = [
        (product_ids[idx], product_names[idx], float(similarity_scores[idx]))
        for idx in sorted_indices
    ]

    return recommended_products