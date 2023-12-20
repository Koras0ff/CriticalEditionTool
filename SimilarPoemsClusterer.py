import os
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import shutil

def load_poems_with_global_index(folder_path):
    global_poems = []
    for subfolder in os.listdir(folder_path):
        subfolder_path = os.path.join(folder_path, subfolder)
        if os.path.isdir(subfolder_path):
            for file in os.listdir(subfolder_path):
                if file.endswith('.json'):
                    file_path = os.path.join(subfolder_path, file)
                    with open(file_path, 'r', encoding='utf-8-sig') as f:
                        data = json.load(f)
                        poem_text = ' '.join(data['latinPlainText']) if isinstance(data['latinPlainText'], list) else data['latinPlainText']
                        global_poems.append((subfolder, poem_text, file))
    return global_poems

def copy_poems_to_folders(output_folder, global_poems, similar_poem_groups):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for group_name, poems_info in similar_poem_groups.items():
        group_folder = os.path.join(output_folder, group_name)
        os.makedirs(group_folder, exist_ok=True)
        for idx, _ in poems_info:  # Correctly unpack the tuple here
            manuscript, _, file_name = global_poems[idx]
            src = os.path.join(folder_path, manuscript, file_name)
            dst = os.path.join(group_folder, file_name)
            shutil.copy2(src, dst)

folder_path = '/Users/enesyilandiloglu/Documents/GitHub/Kakule_1/TextSimilarity/data/TRANSKRİPSİYONLAR'
global_poems = load_poems_with_global_index(folder_path)


# Use global_poems for vectorization
all_poems_texts = [poem[1] for poem in global_poems]  # Extract only the poem text
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(all_poems_texts)
grouped_poems = set()  # To keep track of poems that have already been grouped

similar_poem_groups = {}
group_counter = 1  # Initialize a counter for group naming

for i, (manuscript_i, _, _) in enumerate(global_poems):
    if i in grouped_poems:
        continue  # Skip this poem if it has already been grouped

    group_formed = False
    for j, (manuscript_j, _, _) in enumerate(global_poems):
        if i != j and manuscript_i != manuscript_j and j not in grouped_poems:
            similarity = cosine_similarity(tfidf_matrix[i:i+1], tfidf_matrix[j:j+1])[0][0]
            if similarity >= 0.65:
                group_name = f"Group_{group_counter}"  # Use group_counter for naming
                similar_poem_groups.setdefault(group_name, []).append((j, similarity))
                grouped_poems.add(j)  # Mark the poem as grouped
                group_formed = True

    if group_formed:
        grouped_poems.add(i)  # Mark the initial poem as grouped if it forms a group
        group_counter += 1  # Increment the group counter only if a new group is formed


ungrouped_poems = set(range(len(global_poems)))  # Initialize with all poem indices

ungrouped_poems -= grouped_poems

# Handling ungrouped poems
if ungrouped_poems:
    print("Ungrouped Poems:")
    for idx in ungrouped_poems:
        _, _, file_name = global_poems[idx]
        print(f"  - {file_name}")

# Function to create new clusters for ungrouped poems
def create_new_clusters_for_ungrouped(global_poems, ungrouped_poems, current_group_counter):
    new_clusters = {}
    for idx in ungrouped_poems:
        group_name = f"Group_{current_group_counter}"
        new_clusters[group_name] = [(idx, None)]  # Add as a tuple
        current_group_counter += 1
    return new_clusters

# After your existing clustering process
new_clusters = create_new_clusters_for_ungrouped(global_poems, ungrouped_poems, group_counter)
similar_poem_groups.update(new_clusters)

# After your existing clustering process
new_clusters = create_new_clusters_for_ungrouped(global_poems, ungrouped_poems, group_counter)
similar_poem_groups.update(new_clusters)

# Creating output folders and copying the poems
output_folder = '/Users/enesyilandiloglu/Documents/GitHub/Kakule_1/CompLit/ClusteredPoems'

copy_poems_to_folders(output_folder, global_poems, similar_poem_groups)


# Calculate the average similarity for each group and print details
for group_name, poems_info in similar_poem_groups.items():
    print(f"{group_name}:")

    total_similarity = 0
    for poem_idx, similarity in poems_info:
        manuscript, _, file_name = global_poems[poem_idx]
        for poem_idx, similarity in poems_info:
            if similarity is not None:
                total_similarity += similarity

    average_similarity = total_similarity / len(poems_info)
    print(f"Average Similarity of {group_name}: {average_similarity:.2f}\n")


# Calculate the average similarity for each group
average_similarities = {}
for group_name, poems_info in similar_poem_groups.items():
    total_similarity = sum(similarity for _, similarity in poems_info if similarity is not None)
    average_similarity = total_similarity / len(poems_info)
    average_similarities[group_name] = average_similarity

# Print out average similarities
for group_name, avg_similarity in average_similarities.items():
    print(f"{group_name} Average Similarity: {avg_similarity:.2f}")


import matplotlib.pyplot as plt

# Plotting the average similarities
group_names = list(average_similarities.keys())
avg_sim_values = list(average_similarities.values())

plt.figure(figsize=(10, 6))
plt.bar(group_names, avg_sim_values, color='skyblue')
plt.xlabel('Group')
plt.ylabel('Average Similarity')
plt.title('Average Similarity of Poem Clusters')
plt.xticks(rotation=90)
plt.show()

# Function to print the similarity of each poem within its group
def print_group_similarities(similar_poem_groups, global_poems):
    for group_name, poems_info in similar_poem_groups.items():
        print(f"{group_name}:")
        for poem_idx, similarity in poems_info:
            manuscript, _, file_name = global_poems[poem_idx]
            similarity_text = f"{similarity:.2f}" if similarity is not None else "N/A"
            print(f"  {file_name}", {similarity})
        print()

# Print the similarities for each poem in the groups
print_group_similarities(similar_poem_groups, global_poems)