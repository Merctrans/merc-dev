from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError


class TaskController(http.Controller):
    @http.route(['/task/accept/<int:task_id>'], type='http', auth='user', website=True)
    def accept_task(self, task_id, **kwargs):
        try:
            # Get the task
            task = request.env['project.task'].sudo().browse(task_id)

            # Check if the current user is the assigned contributor
            if task.contributor_id != request.env.user or task.stages_id != 'new':
                return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')

            # Update task status
            task.sudo().write({
                'stages_id': 'in progress',
            })
            
            # Create a message in the chatter
            task.sudo().message_post(
                body=f"Task accepted by {request.env.user.name}",
                message_type='notification'
            )

            # Send email to the PM
            task.sudo().send_email_to_pm(send_type='accepted')

            # Redirect to the form view of the task
            return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')

        except Exception as e:
            return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')

    @http.route(['/task/decline/<int:task_id>'], type='http', auth='user', website=True)
    def decline_task(self, task_id, **kwargs):
        try:
            # Get the task
            task = request.env['project.task'].sudo().browse(task_id)
            
            # Check if the current user is the assigned contributor
            if task.contributor_id != request.env.user or task.stages_id != 'new':
                return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')
            
            # Update task status
            task.sudo().write({
                'stages_id': 'canceled',
            })
            
            # Create a message in the chatter
            task.sudo().message_post(
                body=f"Task declined by {request.env.user.name}",
                message_type='notification'
            )
            
            # Send email to the PM
            task.sudo().send_email_to_pm(send_type='declined')
            
            # Redirect to the form view of the task
            return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')
            
        except Exception as e:
            return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')
