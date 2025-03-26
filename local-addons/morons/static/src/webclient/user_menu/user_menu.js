/** @odoo-module **/

import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { patch } from "@web/core/utils/patch";

patch(UserMenu.prototype, "morons.UserMenu", {
    getElements() {
        // Gọi phương thức gốc để lấy danh sách đã sắp xếp
        const sortedItems = this._super(...arguments);
        
        const excludedIds = ["documentation", "support", "shortcuts", "separator", "account"];
        const filteredItems = sortedItems.filter(item => !excludedIds.includes(item.id));
        
        return filteredItems;
    }
});
