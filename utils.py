from pandas import DataFrame
import matplotlib.pyplot as plt


def ratio(df: DataFrame, feature: str) -> DataFrame:
    """
    Calculate the class distribution ratio of a feature by using the feature with the least samples as the basis
    for the calculation
    :param df: dataframe
    :param feature: which feature should be used for grouping
    :return: ratio for each characteristic
    """
    g = df.groupby([feature]).size().to_frame(name="samples")
    min_samples = g.iloc[:, 0].min()
    g['ratio'] = round(g.iloc[:, 0] / min_samples, 1)
    return g


def piggy_matrix(df: DataFrame):
    f = plt.figure(figsize=(19, 15))
    plt.matshow(df.corr(numeric_only=True), fignum=f.number, cmap="PRGn")
    plt.xticks(range(df.select_dtypes(['number']).shape[1]), df.select_dtypes(['number']).columns, fontsize=14,
               rotation=75)
    plt.yticks(range(df.select_dtypes(['number']).shape[1]), df.select_dtypes(['number']).columns, fontsize=14)
    cb = plt.colorbar()
    cb.ax.tick_params(labelsize=14)
    plt.title('Correlation Matrix', fontsize=16)
    plt.show()
