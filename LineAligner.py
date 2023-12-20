import os
import json
import csv
import torch
from sklearn.feature_extraction.text import CountVectorizer

def matrix_align(x, y, b, threshold=0.5, sim_raw_thr=0,
                 rescale=False, return_alignments=False):
    '''
    Implements the matrix version of the Wagner-Fischer algorithm [1]. 
    
    The algorithm aligns a sequence X against each of a set of
    sequences Y, where sequences consist of numeric vectors.
    The alignment maximizes the sum of weights of edit operations,
    with the substitution weight between two items being their
    dot product and insertion and deletion weight being zero.
    The weights thus represent the similarity of aligned items.
    
    This implementation uses PyTorch (``torch.Tensor``).
    
    Arguments:
        x (Tensor): The embedding matrix X representing a single sequence.
            Each row is a sequence item.
        y (Tensor): The embedding matrix Y representing a corpus
            (set of sequences) to compare against, stacked vertically.
        b (Tensor): The tensor of row indices in the matrix Y indicating
            sequence boundaries. This includes the indices at which a new
            sequence starts, plus ``y.shape[0]`` as last element, so
            that the ``i``-th sequence is contained in ``y[b[i]:b[i+1],:]``.
        threshold (float): The minimum similarity to take into account.
        sim_raw_thr (float): The minimum total similarity of sequences
            to compute alignment for.
        rescale (bool): Rescale similarities to [0,1] after applying
            the threshold: sim_rescaled = (sim-threshold) / (1-threshold)
        return_alignments (bool): return the alignments in
            addition to similarities.
    
    Returns:
        s (Tensor): tensor of size ``b.shape[0]-1`` containing the weight
            of the best alignment between the sequence X and each of the
            sequences from Y.
      if return_alignments == True, also:
        a (Tensor): tensor of size ``Y.shape[0]`` containing for each
            row from the Y matrix the index of the row in X matrix that it
            is aligned to, or -1 if not aligned to any. Note that the
            alignment is computed only if the total similarity between
            the sequences exceeds ``sim_raw_thr``.
        w (Tensor): The weights (similarities) corresponding to the
            aligned pairs in ``a``.
    
    References:
        [1] Maciej Janicki. 2023. Large-scale weighted sequence alignment
            for the study of intertextuality in Finnic oral folk
            poetry. Journal of Data Mining and Digital Humanitites.
    '''

    d = torch.mm(y, x.T)
    if rescale:
        d = (d-threshold) / (1-threshold)
        d[d < 0] = 0
    else:
        d[d < threshold] = 0
    # similarity -> alignment matrix
    d[b[:-1]] = torch.cummax(d[b[:-1]], 1).values
    idx = b[:-1]+1
    idx[torch.isin(idx, b, assume_unique=True)] = 0
    while torch.any(idx > 0):
        idx = idx[idx > 0]
        d[idx,0] = torch.fmax(d[idx-1,0], d[idx,0])
        d[idx,1:d.shape[1]] = torch.fmax(
            d[idx-1,1:d.shape[1]],
            d[idx-1, 0:(d.shape[1]-1)]+d[idx,1:d.shape[1]])
        d[idx,] = torch.cummax(d[idx,], 1).values
        idx += 1
        idx[torch.isin(idx, b, assume_unique=True)] = 0
    if not return_alignments:
        return d[b[1:]-1,-1]
    else:
        # extract the aligned pairs
        # `a` contains for each row in `y` the index of the aligned
        #     counterpart in `x`, or -1 if not aligned
        # `w` contains the weights of the aligned pairs
        a = -torch.ones(d.shape[0], dtype=torch.long)
        w = torch.zeros(d.shape[0], dtype=d.dtype)
        # The alignments are extracted for all poems simultaneously.
        # (i, j) will contain the indices of the currently processed cells
        # In each step, we will advance each index to the next cell
        # on the best-alignment path.
        # If the end of the alignment is reached, the indices are removed.
        i = b[1:]-1
        i = i[d[i,-1] > sim_raw_thr]
        j = torch.ones(i.shape[0], dtype=torch.long) * (d.shape[1]-1)
        if x.device.type == 'cuda':
            # if computing on the GPU -- move also the newly created
            # vectors to the GPU
            a, w, j = a.cuda(), w.cuda(), j.cuda()
        while i.shape[0] > 0:
            # NOT uppermost row of a poem
            u = torch.isin(i, b[:-1], assume_unique=True, invert=True).int()
            v = (j > 0).int()                     # NOT leftmost column
            q = (d[i,j] == d[i-1,j] * u)          # did we come from above?
            r = (d[i,j] == d[i,j-1] * v) * (~q)   # did we come from the left?
            s = (~q) * (~r)                       # did we come from up-left?
            a[i[s]] = j[s]
            w[i[s]] = d[i[s],j[s]] - d[i[s]-1, j[s]-1] * u[s] * v[s]
            i = i - q.int() - s.int()
            j = j - r.int() - s.int()
            # keep the indices if:
            # - we have not crossed a poem boundary (the current i is not the
            #   last row of a poem OR we came from the right)
            # - both i and j are > 0
            keep = (torch.isin(i, b[1:]-1, assume_unique=True, invert=True) + r) \
                   * (i >= 0) * (j >= 0)
            i = i[keep]
            j = j[keep]
        return d[b[1:]-1,-1], a, w


# Function to load data from a JSON file
def load_json_data(file_path):
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        return json.load(file)

# Function to write aligned text to CSV
def write_aligned_to_csv(alignments, headers, file_name):
    with open(file_name, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        for row in alignments:
            writer.writerow(row)

def process_subfolder(subfolder_path, output_folder_path):
    texts = []
    file_names = []
    for filename in os.listdir(subfolder_path):
        if filename.endswith('.json'):
            file_path = os.path.join(subfolder_path, filename)
            data = load_json_data(file_path)
            if 'latinPlainText' in data:
                texts.append(data['latinPlainText'])
                file_names.append(os.path.splitext(filename)[0])  # Get filename without extension

    if texts:
        alignments = process_texts(texts)  # Generate alignments
        output_csv_path = os.path.join(output_folder_path, f'{os.path.basename(subfolder_path)}_alignments.csv')
        headers = file_names  # Use filenames as headers
        write_aligned_to_csv(alignments, headers, output_csv_path)


def process_texts(texts):
    # Flatten the list of corpus texts and compute boundaries
    corpus = [line for text in texts[1:] for line in text]
    boundaries = [0]
    for text in texts[1:]:
        boundaries.append(boundaries[-1] + len(text))
    boundaries_tensor = torch.tensor(boundaries)

    # Vectorize the texts using CountVectorizer
    vectorizer = CountVectorizer(analyzer='char', ngram_range=(2, 2), max_features=100)
    all_texts = corpus + texts[0]
    corpus_bow = vectorizer.fit(all_texts).transform(corpus).toarray()
    target_bow = vectorizer.transform(texts[0]).toarray()

    # Convert bag of bigrams to PyTorch tensors
    emb_x = torch.tensor(target_bow, dtype=torch.float32)
    emb_y = torch.tensor(corpus_bow, dtype=torch.float32)

    # Compute alignments
    _, a, _ = matrix_align(emb_x, emb_y, boundaries_tensor, return_alignments=True)

    # Split 'a' into separate lists of alignments for each text in corpus_texts
    alignments = [a[i:j].tolist() for i, j in zip(boundaries[:-1], boundaries[1:])]

    # Format alignments for CSV
    formatted_alignments = []
    for i, target_line in enumerate(texts[0]):
        row = [target_line]  # Start with the target text line

        # Iterate over each corpus text and their corresponding alignments
        for text, text_alignments in zip(texts[1:], alignments):
            # Check if the current line index 'i' is in the alignments
            aligned_index = text_alignments.index(i) if i in text_alignments else -1
            aligned_line = text[aligned_index] if aligned_index != -1 else ''
            row.append(aligned_line)
        
        formatted_alignments.append(row)

    return formatted_alignments

def process_all_subfolders(main_folder_path, output_folder_path):
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    for subfolder in os.listdir(main_folder_path):
        subfolder_path = os.path.join(main_folder_path, subfolder)
        if os.path.isdir(subfolder_path):
            process_subfolder(subfolder_path, output_folder_path)

# Main folder path containing subfolders
main_folder_path = '/Users/enesyilandiloglu/Documents/GitHub/Kakule_1/CompLit/ClusteredPoems'
output_folder_path = '/Users/enesyilandiloglu/Documents/GitHub/Kakule_1/CompLit/AlignedPoems'  # Replace with your desired output folder path
process_all_subfolders(main_folder_path, output_folder_path)