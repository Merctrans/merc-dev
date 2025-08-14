from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError


class TaskController(http.Controller):
    @http.route(['/task/accept/<int:task_id>'], type='http', auth='user', website=True)
    def accept_task(self, task_id, **kwargs):
        try:
            # contributor login
            user = request.env.user
            # Get the task
            task = request.env['project.task'].sudo().browse(task_id)

            # contributor truy cập lại link trong email sẽ hiện ra form view (nếu đã được phân công)
            if task.contributor_id == user and task.stages_id != 'new':
                return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')

            # Check if user is in the email list but task is already assigned to someone else
            if task.contributor_id and task.contributor_id != user and user in task.contributor_send_email_ids:
                # trang thông báo: Task đã được nhận bởi contributor khác
                # Store notification in session and redirect
                request.session['show_notification'] = {
                    'type': 'warning',
                    'title': 'Job Unavailable',
                    'message': 'This job is no longer available.'
                }
                return request.redirect('/web#view_type=list&model=project.task')

            update_vals = {}

            # Task chưa có contributor, năm trong danh sách gửi email, trạng thái new
            if not task.contributor_id and user in task.contributor_send_email_ids and task.stages_id == 'new':
                update_vals.update({
                    'contributor_id': user.id,
                    'stages_id': 'in progress'
                })
            # Task đã có contributor, và user là contributor được phân công, trạng thái new
            elif task.contributor_id == user and task.stages_id == 'new':
                update_vals.update({
                    'stages_id': 'in progress'
                })

            # Update task status
            if update_vals:
                task.sudo().with_context(from_contributor=True).write(update_vals)

                # Create a message in the chatter
                task.sudo().message_post(
                    body=f"Task accepted by {request.env.user.name}",
                    message_type='notification'
                )

                # Send email to the PM
                task.sudo().send_email_to_pm(send_type='accepted')

                # Redirect to the form view of the task
                return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')
            # Redirect to task list for other cases
            return request.redirect(f'/web#view_type=list&model=project.task')

        except Exception as e:
            return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')

    @http.route(['/task/decline/<int:task_id>'], type='http', auth='user', website=True)
    def decline_task(self, task_id, **kwargs):
        try:
            # contributor login
            user = request.env.user
            # Get the task
            task = request.env['project.task'].sudo().browse(task_id)

            # Check if user is in the email list but task is already assigned to someone else
            if task.contributor_id and task.contributor_id != user:
                # trang thông báo: Task đã được nhận bởi contributor khác
                # Store notification in session and redirect
                request.session['show_notification'] = {
                    'type': 'warning',
                    'title': 'Job Unavailable',
                    'message': 'This job is no longer available.'
                }
                return request.redirect('/web#view_type=list&model=project.task')

            # Check if the current user is the assigned contributor
            if task.contributor_id and task.contributor_id == user and task.stages_id != 'new':
                return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')

            if task.contributor_id and task.contributor_id == user and task.stages_id == 'new':
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
            if task.contributor_id and task.contributor_id == user:
                return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')
            else:
                return request.redirect('/web#view_type=list&model=project.task')

        except Exception as e:
            return request.redirect(f'/web#id={task.id}&view_type=form&model=project.task')

    @http.route(['/web/session/get_notification'], type='json', auth='user')
    def get_notification(self, **kwargs):
        """Get notification from session"""
        notification = request.session.get('show_notification')
        if notification:
            # Clear it after getting
            del request.session['show_notification']
        return notification
