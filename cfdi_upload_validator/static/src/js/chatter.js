/** @odoo-module **/

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { useService } from "@web/core/utils/hooks";
import { AttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { Chatter } from "@mail/core/web/chatter";

import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    setup() {
        console.log("Chatter.prototype ................... ")
        super.setup(...arguments);
    },

    onClickAddAttachments() {
        console.log("111 onClickAddAttachments ................... ");
        console.log("this.state ................... ", this.state);
        console.log("this ................... ", this);
        console.log("this.state.thread.model ................... ", this.state.thread.model);
        const res_model = this.state.thread.model;
        const res_id = this.state.thread.id;

        console.log("res_model ................... ", res_model);
        console.log("res_id ................... ", res_id);

        // thread.model
        if (this.attachments.length === 0) {
            return;
        }
        this.state.isAttachmentBoxOpened = !this.state.isAttachmentBoxOpened;
        if (this.state.isAttachmentBoxOpened) {
            this.rootRef.el.scrollTop = 0;
            this.state.thread.scrollTop = "bottom";
        }
    },

    async onUploaded(data) {
        console.log("2222 onUploaded ................... ");
        console.log("this.state ................... ", this.state);
        console.log("this ................... ", this);
        console.log("this.state.thread.model ................... ", this.state.thread.model);
        const res_model = this.state.thread.model;
        const res_id = this.state.thread.id;

        console.log("res_model ................... ", res_model);
        console.log("res_id ................... ", res_id);
        console.log("data ................... ", data);

        /*const attachments = await this.orm.silent.call("ir.attachment", "search", [
                [('res_id','=',res_id),('res_model','=',res_model),]
            ]);*/

        const [attachment_ok, new_data] = await this.orm.silent.call("account.move", "validate_attachments_xml", [
                'validaciones',
                res_model,
                res_id,
                data,
            ]);

        console.log('NEW DATA:  ', new_data)
        

        await this.attachmentUploader.uploadData(data);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
        this.state.isAttachmentBoxOpened = true;
        if (this.rootRef.el) {
            this.rootRef.el.scrollTop = 0;
        }
        this.state.thread.scrollTop = "bottom";
    },

    async onClickAttachFile(ev) {

        console.log("33333 onClickAttachFile ................... ");
        console.log("ev ................... ", ev);
        console.log("this ................... ", this);
        console.log("this.props. ................... ", this.props);
        /*const files = Array.from(ev.target.files);
        console.log("files ............. ", files);*/
        console.log("this.state.thread ................... ", this.state.thread);
        console.log("this.state.thread.id ................... ", this.state.thread.id);
        const res_model = this.state.thread.model;
        const res_id = this.state.thread.id;
        console.log("res_model ................... ", res_model);
        console.log("res_id ................... ", res_id);
        if (this.state.thread.id) {
            return;
        }
        const saved = await this.props.saveRecord?.();
        console.log("saved ................... ", saved);
        if (!saved) {
            return false;
        }
    }


});

