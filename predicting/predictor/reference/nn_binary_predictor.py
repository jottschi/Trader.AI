'''
Created on 08.11.2017

@author: rmueller
'''
from model.IPredictor import IPredictor
import numpy as np

from model.StockData import StockData
from utils import load_keras_sequential, save_keras_sequential, read_stock_market_data
from model.CompanyEnum import CompanyEnum
from logger import logger
from matplotlib import pyplot as plt
from keras.models import Sequential
from keras.layers import Dense
from keras.layers.normalization import BatchNormalization
from keras.layers.advanced_activations import LeakyReLU
from keras.callbacks import ReduceLROnPlateau
from definitions import PERIOD_1, PERIOD_2, PERIOD_3

RELATIVE_PATH = 'predicting/predictor/reference/nn_binary_predictor_data'
MODEL_FILE_NAME_STOCK_A = 'nn_binary_predictor_stock_a_network'
MODEL_FILE_NAME_STOCK_B = 'nn_binary_predictor_stock_b_network'

# Neural network configuration
INPUT_SIZE = 400
FIRST_LAYER_SIZE = 200 
SECOND_LAYER_SIZE = 20 
OUTPUT_SIZE = 1
ACTIVATION_FUNCTION_FOR_OUTPUT = 'sigmoid'
LOSS_FUNCTION = 'binary_crossentropy'
OPTIMIZER = 'rmsprop'
METRICS = ['accuracy']

class BaseNnBinaryPredictor(IPredictor):
    '''
    Perfect predictor based on an already trained neural network.
    '''

    def __init__(self, nn_filename : str):
        '''
        Constructor: Load the trained and stored neural network.
        '''
        # Try loading a stored trained neural network...
        self.trained = True
        self.model = load_keras_sequential(RELATIVE_PATH, nn_filename)
        # ... if that wasn't possible, then create a new untrained one
        if self.model is None:
            logger.warn(f"BaseNnPredictor: Loading of trained neural network failed, creating a new untrained one.")
            self.trained = False
            self.model = create_model()
            
        self.model.compile(loss=LOSS_FUNCTION, optimizer=OPTIMIZER, metrics=METRICS)
        
    def doPredict(self, data: StockData) -> float:
        """ Use the loaded trained neural network to predict the next stock value.
    
        Args:
          data : historical stock values of a company
        Returns:
          predicted next stock value for that company
        """
        # TODO diese Assumptions hier sind Mist, da fehlt uns eine Klasse für
        # Assumptions about data: at least INPUT_SIZE pairs of type (_, float)
        assert data.get_row_count() >= INPUT_SIZE
        assert len(data.get_first()) == 2
        assert isinstance(data.get_first()[1], float)

        # Extract last INPUT_SIZE floats (here: stock values) as input for neural network (format: numpy array of arrays)
        input_values = np.array([[x[1] for x in data.get_from_offset(-INPUT_SIZE)]])
        
        normalized_prices = []

        vector_min = np.min(input_values)
        vector_max = np.max(input_values)
        
        for price in input_values:
            normalized_prices.append((price - vector_min) / (vector_max - vector_min))
            
        input_values = np.asarray(normalized_prices)

        try:
            # Let network predict the next stock value based on last 100 stock values
            prediction = self.model.predict(input_values)[0][0]
            return data.get_last()[1] + self.convert_nn_output_to_value(prediction)
        except:
            logger.error("Error in predicting next stock value.")
            assert False
            
    def convert_nn_output_to_value(self, nn_output) -> float:
    
        if(nn_output > 0.6):
            return 1.0
        elif(nn_output < 0.4):
            return -1.0
        else:
            return 0.0


class StockANnBinaryPredictor(BaseNnBinaryPredictor):
    '''
    Perfect predictor for stock A based on an already trained neural network.
    '''

    def __init__(self):
        '''
        Constructor: Load the trained and stored neural network.
        '''
        super().__init__(MODEL_FILE_NAME_STOCK_A)


class StockBNnBinaryPredictor(BaseNnBinaryPredictor):
    '''
    Perfect predictor for stock B based on an already trained neural network.
    '''

    def __init__(self):
        '''
        Constructor: Load the trained and stored neural network.
        '''
        super().__init__(MODEL_FILE_NAME_STOCK_B)

###############################################################################
# The following code trains and stores the corresponding neural network
###############################################################################


def learn_nn_and_save(training_data: StockData, test_data: StockData, filename_to_save:str):
    
    training_dates = training_data.get_dates()
    training_prices = training_data.get_values()
    
    # Build chunks of prices from 100 consecutive days (input_training_prices) and 101th day (current_prices_for_plot)
    input_training_prices, current_prices_for_plot, wanted_results = [], [], []

    for i in range(0, len(training_prices) - INPUT_SIZE):
        last_price_vector = training_prices[i:INPUT_SIZE + i]
        
        normalized_prices = []
        normalized_prices_sigma = []

        vector_min = np.min(last_price_vector)
        vector_max = np.max(last_price_vector)
        mean = np.mean(last_price_vector)
        std = np.std(last_price_vector)
        
        for price in last_price_vector:
            normalized_prices.append((price - vector_min) / (vector_max - vector_min))
            normalized_prices_sigma.append((price - mean) / std)

        last_price_vector = normalized_prices
        
        input_training_prices.append(last_price_vector)
        
        current_price = training_prices[INPUT_SIZE + i]
        current_prices_for_plot.append(current_price)
        
        previous_price = training_prices[INPUT_SIZE + i - 1 ]
        
        delta = (current_price - previous_price)
            
        direction = 0.5    
        if(delta <= -0.0000001) :
            # Sell
            direction = 0.0
        elif (delta >= 0.0000001):
            # Buy
            direction = 1.0
        
        wanted_results.append(direction)
        
    test_prices = test_data.get_values()
    input_test_prices, wanted_test_results = [], []
    for i in range(0, len(test_prices) - INPUT_SIZE):
        last_price_vector = test_prices[i:INPUT_SIZE + i]
        
        normalized_prices = []

        vector_min = np.min(last_price_vector)
        vector_max = np.max(last_price_vector)
        mean = np.mean(last_price_vector)
        std = np.std(last_price_vector)
        
        for price in last_price_vector:
            normalized_prices.append((price - vector_min) / (vector_max - vector_min))

        last_price_vector = normalized_prices
        
        input_test_prices.append(last_price_vector)
        
        current_price = training_prices[INPUT_SIZE + i]
        previous_price = training_prices[INPUT_SIZE + i - 1 ]
        delta = (current_price - previous_price)
            
        direction = 0.5    
        if(delta <= -0.0000001) :
            # Sell
            direction = 0.0
        elif (delta >= 0.0000001):
            # Buy
            direction = 1.0
        
        wanted_test_results.append(direction)   
    

    # Shape and configuration of network is optimized for binary classification problems - see: https://keras.io/getting-started/sequential-model-guide/ 
    network = create_model()
     
    network.compile(optimizer=OPTIMIZER, loss=LOSS_FUNCTION, metrics=METRICS)

    # Train the neural network
    reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.9, patience=5, min_lr=0.000001, verbose=1) 
    history = network.fit(input_training_prices, wanted_results, epochs=500, batch_size=128, verbose=1, validation_data=(input_test_prices, wanted_test_results), shuffle=True, callbacks=[reduce_lr])

    # Evaluate the trained neural network and plot results
    score = network.evaluate(input_training_prices, wanted_results, batch_size=128, verbose=0)
    logger.debug(f"Test score: {score}")
    
    # Draw
    plt.figure()
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss']) 
    plt.plot(history.history['acc'])
    plt.title('training loss / testing loss by epoch')
    plt.ylabel('loss/acc')
    plt.xlabel('epoch')
    plt.legend(['loss', 'val_loss', 'acc'], loc='best')
    plt.figure()
    currentPrice_prediction = network.predict(input_training_prices, batch_size=128)
        
    logger.debug(f"currentPrice_prediction:")
    iteration = 0
    for x in currentPrice_prediction:
        logger.debug(f"iteration {iteration} - output: {x}")
        iteration = iteration + 1
        
    plt.plot(training_dates[INPUT_SIZE:], current_prices_for_plot, color="black")  # current prices in reality
    plt.plot(training_dates[INPUT_SIZE:], [calculate_delta(x) for x in currentPrice_prediction], color="green")  # predicted prices by neural network
    plt.title('current prices / predicted prices by date')
    plt.ylabel('price')
    plt.xlabel('date')
    plt.legend(['current', 'predicted'], loc='best')
    plt.show()

    # Save trained model: separate network structure (stored as JSON) and trained weights (stored as HDF5)
    save_keras_sequential(network, RELATIVE_PATH, filename_to_save)

def create_model() -> Sequential:
    # Shape and configuration of network is optimized for binary classification problems - see: https://keras.io/getting-started/sequential-model-guide/ 
    network = Sequential()
    
    # Input layer
    network.add(Dense(FIRST_LAYER_SIZE, input_dim=INPUT_SIZE))
    network.add(BatchNormalization())
    network.add(LeakyReLU())
     
    # First hidden layer
    network.add(Dense(SECOND_LAYER_SIZE))
    network.add(BatchNormalization())
    network.add(LeakyReLU())
    
    # Output layer
    network.add(Dense(OUTPUT_SIZE, activation=ACTIVATION_FUNCTION_FOR_OUTPUT))
    
    return network


def calculate_delta(nn_output) -> float:
    
    if(nn_output > 0.6):
        return 1.0
    elif(nn_output < 0.4):
        return -1.0
    else:
        return 0.0


if __name__ == "__main__":
    # Load the training data; here: complete data about stock A (Disney)
    logger.debug("Data loading...")
    training_stock_market_data = read_stock_market_data([CompanyEnum.COMPANY_A, CompanyEnum.COMPANY_B], [PERIOD_1, PERIOD_2])
    test_stock_market_data = read_stock_market_data([CompanyEnum.COMPANY_A, CompanyEnum.COMPANY_B], [PERIOD_3])
    
    company_a_training_stock_data: StockData = training_stock_market_data[CompanyEnum.COMPANY_A]
    company_a_test_stock_data: StockData = test_stock_market_data[CompanyEnum.COMPANY_A]
    
    logger.debug(f"Data for Stock A loaded")
    learn_nn_and_save(company_a_training_stock_data, company_a_test_stock_data, MODEL_FILE_NAME_STOCK_A)
    
    company_b_training_stock_data: StockData = training_stock_market_data[CompanyEnum.COMPANY_B]
    company_b_test_stock_data: StockData = test_stock_market_data[CompanyEnum.COMPANY_B]
    
    logger.debug(f"Data for Stock B loaded")
    learn_nn_and_save(company_b_training_stock_data, company_b_test_stock_data, MODEL_FILE_NAME_STOCK_B)

