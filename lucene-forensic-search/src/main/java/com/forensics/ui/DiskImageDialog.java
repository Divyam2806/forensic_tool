package com.forensics.ui;

import com.forensics.casework.CaseInfo;
import com.forensics.imaging.DiskImagingService;

import javax.swing.*;
import java.awt.*;
import java.nio.file.Path;

public class DiskImageDialog extends JDialog {
    private final JTextField sourceField = new JTextField(28);
    private final JTextField imageNameField = new JTextField("disk_image.img", 20);
    private final JLabel statusLabel = new JLabel(" ");
    private boolean completed;

    public DiskImageDialog(Frame owner, CaseInfo activeCase) {
        super(owner, "Create Disk Image", true);

        JButton browseButton = new JButton("Browse");
        JButton createButton = new JButton("Create Image");
        JButton cancelButton = new JButton("Cancel");

        browseButton.addActionListener(e -> chooseSource(owner));

        createButton.addActionListener(e -> {
            try {
                String sourceText = sourceField.getText().trim();
                if (sourceText.isEmpty()) {
                    showStatus("Choose a source path first.", true);
                    return;
                }
                Path source = Path.of(sourceText);
                String imageName = imageNameField.getText().trim();
                if (imageName.isEmpty()) {
                    imageName = "disk_image.img";
                }
                if (!imageName.endsWith(".img")) {
                    imageName = imageName + ".img";
                }
                Path imagePath = activeCase.casePath().resolve("images").resolve(imageName);
                DiskImagingService service = new DiskImagingService();
                var result = service.createImage(source, imagePath);
                showStatus("Image created. SHA-256 source: " + shortHash(result.sourceHash()) +
                        " | image: " + shortHash(result.imageHash()), false);
                JOptionPane.showMessageDialog(this,
                        "Disk image created:\n" + result.imagePath() +
                                "\nSource hash: " + result.sourceHash() +
                                "\nImage hash: " + result.imageHash(),
                        "Imaging complete",
                        JOptionPane.INFORMATION_MESSAGE);
                completed = true;
                dispose();
            } catch (Exception ex) {
                showStatus(ex.getMessage(), true);
            }
        });

        cancelButton.addActionListener(e -> {
            completed = false;
            dispose();
        });

        JPanel form = new JPanel(new GridBagLayout());
        form.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));
        GridBagConstraints gc = new GridBagConstraints();
        gc.insets = new Insets(8, 8, 8, 8);
        gc.fill = GridBagConstraints.HORIZONTAL;
        gc.gridy = 0;
        gc.gridx = 0;
        form.add(new JLabel("Source path"), gc);
        gc.gridx = 1;
        form.add(sourceField, gc);
        gc.gridx = 2;
        form.add(browseButton, gc);

        gc.gridy = 1;
        gc.gridx = 0;
        form.add(new JLabel("Image name"), gc);
        gc.gridx = 1;
        gc.gridwidth = 2;
        form.add(imageNameField, gc);

        gc.gridy = 2;
        gc.gridx = 0;
        gc.gridwidth = 3;
        statusLabel.setForeground(new Color(108, 117, 125));
        form.add(statusLabel, gc);

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        buttons.add(cancelButton);
        buttons.add(createButton);

        JPanel root = new JPanel(new BorderLayout(10, 10));
        root.setBorder(BorderFactory.createEmptyBorder(16, 16, 16, 16));
        root.add(form, BorderLayout.CENTER);
        root.add(buttons, BorderLayout.SOUTH);

        setContentPane(root);
        setMinimumSize(new Dimension(720, 240));
        pack();
        setLocationRelativeTo(owner);
        getRootPane().setDefaultButton(createButton);
    }

    private void chooseSource(Component owner) {
        JFileChooser chooser = new JFileChooser();
        chooser.setFileSelectionMode(JFileChooser.FILES_AND_DIRECTORIES);
        chooser.setDialogTitle("Choose source file or disk path");
        if (chooser.showOpenDialog(owner) == JFileChooser.APPROVE_OPTION) {
            sourceField.setText(chooser.getSelectedFile().getAbsolutePath());
            showStatus("Source selected.", false);
        }
    }

    private void showStatus(String message, boolean error) {
        statusLabel.setText(message);
        statusLabel.setForeground(error ? new Color(180, 53, 53) : new Color(108, 117, 125));
    }

    private String shortHash(String hash) {
        if (hash == null || hash.equals("unavailable")) return "unavailable";
        return hash.substring(0, Math.min(16, hash.length())) + "...";
    }

    public boolean showDialog() {
        setVisible(true);
        return completed;
    }
}
