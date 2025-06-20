from flask import Blueprint, request, jsonify , current_app
from datetime import datetime
from api.extensions import db
from api.models.Order import Order
from api.models.order_status import OrderStatus
from api.models.Hero import Hero
from api.models.Meal import Meal
from api.schemas.order_schema import OrderSchema
from sqlalchemy.exc import SQLAlchemyError
from api.extensions import task_queue

order_blueprint = Blueprint("order_blueprint", __name__, url_prefix="/orders")
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)



#--------FETCH ALL ORDERS --------#
@order_blueprint.route('/', methods=['GET'])
def get_orders():
    try:
        current_app.logger.info(f"getting all orders")

        orders = Order.query.order_by(Order.order_time.desc()).all()
        return orders_schema.jsonify(orders)
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500

#--------FETCH  ORDER BY ID --------#
@order_blueprint.route('/<int:order_id>', methods=['GET'])
def get_order(order_id):
    current_app.logger.info(f"getting all order {order_id} data")

    order = Order.query.get_or_404(order_id)
    return order_schema.jsonify(order)




#--------CREATE A NEW ORDER --------#
@order_blueprint.route('/', methods=['POST'])
def create_order():
    data = request.get_json()
    current_app.logger.info(f"creating new order :{data}")
    
    # Validate and deserialize input
    order = order_schema.load(data)
    
    db.session.add(order)
    db.session.commit()
    
    current_app.logger.info(f"Order {order.id} saved, continue to processing")

    
    task_queue.enqueue("worker.tasks.process_order" , order.id)
    
    return order_schema.jsonify(order), 202

#--------UPDATE THE WHOLE ORDER --------#
@order_blueprint.route('/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        current_app.logger.info(f"updating the order #{order_id}")

        
        if not all(field in data for field in ['hero_id', 'meal_id']):
            return jsonify({"error": "Missing hero_id or meal_id"}), 400
            
        order.hero = Hero.query.get_or_404(data['hero_id'])
        order.meal = Meal.query.get_or_404(data['meal_id'])
        
        if 'status' in data:
            new_status = OrderStatus(data['status'])
            
            
                
            order.status = new_status
            
            if new_status == OrderStatus.COMPLETED and not order.completed_time:
                order.completed_time = datetime.utcnow()
        
        if 'message' in data:
            order.message = data['message']
            
        db.session.commit()
        current_app.logger.info(f"Order #{order_id} updated")

        return order_schema.jsonify(order)
    except ValueError as e:
        current_app.logger.info(f"an error has occured while updating the order #{order_id} , {str(e)}")

        return jsonify({"error": "Invalid order status"}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.info(f"an error has occured while updating the order #{order_id} , {str(e)}")

        return jsonify({"error": str(e)}), 400

#--------UPDATE AN ORDER PARITALY --------#
@order_blueprint.route('/<int:order_id>', methods=['PATCH'])
def partial_update_order(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        current_app.logger.info(f"Updating order #{order_id}")

        if 'status' in data:
            new_status = OrderStatus(data['status'])
            
            
                
            order.status = new_status
            
            if new_status == OrderStatus.COMPLETED and not order.completed_time:
                order.completed_time = datetime.utcnow()
        
        if 'message' in data:
            order.message = data['message']
            
        db.session.commit()
        return order_schema.jsonify(order)
    except ValueError as e:
        current_app.logger.info(f"an error has occured while updating the order #{order_id} , {str(e)}")

        return jsonify({"error": "Invalid order status"}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.info(f"an error has occured while updating the order #{order_id} , {str(e)}")

        return jsonify({"error": str(e)}), 400
    
    
    
    

#--------DELETE AN ORDER --------#
@order_blueprint.route('/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    try:
        current_app.logger.info(f"deleting order #{order_id}")

        order = Order.query.get_or_404(order_id)
        db.session.delete(order)
        db.session.commit()
        return jsonify({"message": f"Order {order_id} deleted successfully"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.info(f"an error has occured while deleting the order #{order_id} , {str(e)}")
        
        return jsonify({"error": str(e)}), 400
    
    
    
    

#--------FETCH AN ORDER BY ITS STATUS --------#
@order_blueprint.route('/status/<status>', methods=['GET'])
def get_orders_by_status(status):
    try:
        current_app.logger.info(f"Getting orders with the status : {status}")

        status_enum = OrderStatus(status)
        orders = Order.query.filter_by(status=status_enum).order_by(Order.order_time.desc()).all()
        return orders_schema.jsonify(orders)
    except ValueError:
        current_app.logger.info(f"an error has occured while getting the orders by status : {status}")

        return jsonify({"error": "Invalid order status", "valid_statuses": [s.value for s in OrderStatus]}), 400