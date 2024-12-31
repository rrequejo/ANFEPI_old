/** @odoo-module **/

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { useService } from "@web/core/utils/hooks";
import { AttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { Chatter } from "@mail/core/web/chatter";


class CustomAttachmentUploader extends AttachmentUploader {
    /**
     * Override to add custom validation logic for file uploads.
     * @override
     */
    async _onInputFileChange(event) {
        console.log("_onInputFileChange ............. ");
        const files = Array.from(event.target.files);
        console.log("files ............. ", files);
        for (const file of files) {
            // Example: Validate file size (limit: 5 MB)
            if (file.size > 5 * 1024 * 1024) {
                Dialog.alert(this, {
                    title: "Invalid File",
                    body: `The file ${file.name} exceeds the size limit of 5 MB.`,
                });
                return;
            }
            // Example: Validate file type
            if (!['application/pdf', 'image/jpeg'].includes(file.type)) {
                Dialog.alert(this, {
                    title: "Invalid File Type",
                    body: `The file ${file.name} is not of an allowed type. Only PDF and JPEG files are accepted.`,
                });
                return;
            }
        }
        // Call parent logic if validation passes
        await super._onInputFileChange(event);
    }
}

// Register the custom uploader component in the component registry
registry.category("components").add("CustomAttachmentUploader", CustomAttachmentUploader);