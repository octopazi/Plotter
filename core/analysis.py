import numpy as np

class TrendlineAnalyzer:
    """Provides mathematical utility for data fitting and trendline generation."""
    
    @staticmethod
    def fit_trendline(x_data, y_data, trend_type):
        """
        Fits data based on trend_type. 
        Returns (x_span, y_span, label_string) or (None, None, None) on failure.
        """
        # 1. Select the Data Mask to avoid Math Domain Errors (log(0), log(-ve))
        mask = np.ones(len(x_data), dtype=bool)
        if trend_type in ["Logarithmic", "Power"]:
            mask &= (x_data > 0)
        if trend_type in ["Exponential", "Power"]:
            mask &= (y_data > 0)
            
        x_clean = x_data[mask]
        y_clean = y_data[mask]
        
        if len(x_clean) < 2:
            return None, None, None
            
        try:
            # Generate 200 points for a smooth curve
            x_span = np.linspace(x_clean.min(), x_clean.max(), 200)
            
            if trend_type == "Linear":
                m, c = np.polyfit(x_clean, y_clean, 1)
                y_span = m * x_span + c
                label = f'Linear: y = {m:.4g}x + {c:.4g}'
                
            elif trend_type == "Exponential":
                m, c = np.polyfit(x_clean, np.log(y_clean), 1)
                a = np.exp(c)
                y_span = a * np.exp(m * x_span)
                label = f'Exponential: y = {a:.4g}e^({m:.4g}x)'
                
            elif trend_type == "Logarithmic":
                m, c = np.polyfit(np.log(x_clean), y_clean, 1)
                y_span = m * np.log(x_span) + c
                label = f'Logarithmic: y = {m:.4g}ln(x) + {c:.4g}'
                
            elif trend_type == "Power":
                m, c = np.polyfit(np.log(x_clean), np.log(y_clean), 1)
                a = np.exp(c)
                y_span = a * (x_span ** m)
                label = f'Power: y = {a:.4g}x^({m:.4g})'
            else:
                return None, None, None
                
            return x_span, y_span, label
            
        except Exception as e:
            print(f"Trendline fit failure ({trend_type}): {e}")
            return None, None, None
