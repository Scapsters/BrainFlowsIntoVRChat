import pickle
import numpy as np
import tensorflow as tf
from keras.models import Sequential
from keras.layers import GRU, Dense
from keras.utils import to_categorical
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import classification_report

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowPresets
from brainflow.data_filter import DataFilter, DetrendOperations, NoiseTypes, WaveletTypes, FilterTypes, WindowOperations

## Assuming the preprocess_data and extract_features functions remain unchanged

def create_gru_model(input_shape):
    model = Sequential([
        GRU(128, input_shape=input_shape, return_sequences=True),
        GRU(64),
        Dense(32, activation='relu'),
        Dense(2, activation='softmax')  # Assuming binary classification
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

## preprocess and extract features to be shared between train and test

def preprocess_data(session_data, sampling_rate):
    for eeg_chan in range(len(session_data)):
        DataFilter.remove_environmental_noise(session_data[eeg_chan], sampling_rate, NoiseTypes.FIFTY_AND_SIXTY.value)
        DataFilter.perform_bandpass(session_data[eeg_chan], sampling_rate, 30, 100, 6, FilterTypes.BUTTERWORTH_ZERO_PHASE.value, 0) # only beta and gamma
        DataFilter.detrend(session_data[eeg_chan], DetrendOperations.LINEAR)
    return session_data

def extract_features(preprocessed_data):
    features  = []
    for eeg_row in preprocessed_data:
        intent_wavelet_coeffs, intent_lengths = DataFilter.perform_wavelet_transform(eeg_row, WaveletTypes.DB4, 5)
        features.extend(intent_wavelet_coeffs)
        # fft_data = DataFilter.perform_fft(eeg_row, WindowOperations.NO_WINDOW.value)
        # features.extend(np.abs(fft_data))
    return np.array(features)

## helper function to generate windows

def segment_data(eeg_data, samples_per_window, overlap=0):
    _, total_samples = eeg_data.shape
    step_size = samples_per_window - overlap
    windows = []

    for start in range(0, total_samples - samples_per_window + 1, step_size):
        end = start + samples_per_window
        window = eeg_data[:, start:end]
        windows.append(window)

    return np.array(windows)

def main():
    ## Load recorded data details
    with open("recorded_eeg.pkl", "rb") as f:
        recorded_data = pickle.load(f)
    board_id = recorded_data['board_id']
    intent_sessions = recorded_data['intent_data']
    baseline_sessions = recorded_data['baseline_data']
    sampling_rate = BoardShim.get_sampling_rate(board_id)
    eeg_channels = BoardShim.get_eeg_channels(board_id)

    ## generate sample windows from recorded data
    window_size = 1 * sampling_rate
    intent_sessions = [data[eeg_channels] for data in intent_sessions]
    baseline_sessions = [data[eeg_channels] for data in baseline_sessions]

    overlap = int(window_size * 0.93)
    intent_windows = np.concatenate([segment_data(session, window_size, overlap) for session in intent_sessions])
    baseline_windows = np.concatenate([segment_data(session, window_size, overlap) for session in baseline_sessions])

    ## extract the features from the windows
    intent_feature_windows = []
    baseline_feature_windows = []

    for session_data in intent_windows:
        preprocessed_data = preprocess_data(session_data, sampling_rate)
        feature_windows = extract_features(preprocessed_data)
        intent_feature_windows.append(feature_windows)

    for session_data in baseline_windows:
        preprocessed_data = preprocess_data(session_data, sampling_rate)
        feature_windows = extract_features(preprocessed_data)
        baseline_feature_windows.append(feature_windows)

    ## Combine features from all sessions and create labels
    feature_windows = np.concatenate((intent_feature_windows, baseline_feature_windows))
    labels = np.array(["button"] * len(intent_feature_windows) + ["baseline"] * len(baseline_feature_windows))

    ## Encode labels
    label_encoder = LabelEncoder()
    labels_encoded = label_encoder.fit_transform(labels)
    labels_categorical = to_categorical(labels_encoded)

    ## Scale features
    feature_scaler = StandardScaler()
    scaled_feature_windows = feature_scaler.fit_transform(feature_windows)

    ## Apply PCA after scaling
    feature_pca = PCA(n_components=0.95)  # Retain 95% of variance
    pca_feature_windows = feature_pca.fit_transform(scaled_feature_windows)

    ## Reshape data for GRU input if necessary
    # Assuming you know the number of time steps and features after PCA
    num_samples, num_features = pca_feature_windows.shape
    # You need to determine `time_steps` based on your data's temporal structure
    # For this example, let's assume each sample is already appropriately segmented
    time_steps = 1  # This should be changed based on your actual data structure
    pca_feature_windows_reshaped = pca_feature_windows.reshape((num_samples, time_steps, num_features))

    ## Create train and test sets
    X_train, X_test, y_train, y_test = train_test_split(pca_feature_windows_reshaped, labels_categorical, test_size=0.25, shuffle=True)

    ## Create and train the GRU model
    input_shape = (time_steps, num_features)  # Adjust based on your data reshaping
    model = create_gru_model(input_shape)
    model.fit(X_train, y_train, epochs=10, batch_size=64, validation_split=0.2)

    ## Evaluate the model
    test_loss, test_acc = model.evaluate(X_test, y_test)
    print(f"Test Accuracy: {test_acc}")

    # Predict classes with the model
    y_pred = model.predict(X_test)
    # Convert predictions and true labels to label encoded form
    y_pred_labels = np.argmax(y_pred, axis=1)
    y_true_labels = np.argmax(y_test, axis=1)

    # Generate a classification report
    print(classification_report(y_true_labels, y_pred_labels, target_names=label_encoder.classes_))

    ## Save models for realtime use
    model.save('gru_model.keras')  # Save the entire model
    model_dict = {
        'label_encoder' : label_encoder,
        'feature_scaler' : feature_scaler,
        'feature_pca' : feature_pca
    }
    with open('model_dict.pkl', 'wb') as f:
        pickle.dump(model_dict, f)

if __name__ == "__main__":
    main()
