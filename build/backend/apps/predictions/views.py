from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .ml.predict import get_predictor

class PredictMatchView(APIView):
    
    def post(self, request):
        required_fields = ['team_xg', 'opponent_xg', 'is_home']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {'error': f'Missing required field: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        model_name = request.data.get('model', 'understat_epl_2024')
        
        try:
            predictor = get_predictor(model_name)
            result = predictor.predict(
                team_xg=float(request.data['team_xg']),
                opponent_xg=float(request.data['opponent_xg']),
                is_home=bool(request.data['is_home']),
            )
            result['model_used'] = model_name
            return Response(result)
        
        except FileNotFoundError:
            return Response(
                {'error': f'Model not found: {model_name}'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PredictBatchView(APIView):
    
    def post(self, request):
        if 'matches' not in request.data:
            return Response(
                {'error': 'Missing required field: matches'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        matches = request.data['matches']
        
        if not isinstance(matches, list):
            return Response(
                {'error': 'matches must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            predictor = get_predictor()
            results = predictor.predict_batch(matches)
            return Response({'predictions': results})
        
        except FileNotFoundError:
            return Response(
                {'error': 'Model not found. Please train a model first.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModelInfoView(APIView):
    
    def get(self, request):
        try:
            predictor = get_predictor()
            return Response({
                'status': 'loaded',
                'features': predictor.feature_columns,
            })
        except FileNotFoundError:
            return Response({
                'status': 'not_found',
                'features': [],
            })