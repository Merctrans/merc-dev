/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, xml } from "@odoo/owl";

export class SessionNotification extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        onMounted(() => {
            this.checkSessionNotification();
        });
    }

    async checkSessionNotification() {
        try {
            // Call RPC to get notification data
            const notificationData = await this.rpc('/web/session/get_notification', {});
            if (notificationData) {
                // Show notification
                this.notification.add(notificationData.message, {
                    type: notificationData.type || 'warning',
                    title: notificationData.title || 'Notification',
                    sticky: true
                });
            } else {
                console.log("No notification found in session");
            }
        } catch (error) {
            console.error('Error checking session notification:', error);
        }
    }
}

// Use a simple template without external XML file
SessionNotification.template = xml`
    <div style="display: none;">
        <!-- Hidden component that just handles notifications -->
    </div>
`;

registry.category("main_components").add("SessionNotification", {
    Component: SessionNotification,
}); 